#!/usr/bin/env python3
"""
corpus_stats_viz.py
webannoparser 
11/19/18
Copyright (c) Gilles Jacobs. All rights reserved.  
"""
from parser import *
from parse_project import parse_corpus, parse_project
import pygal
import pickle
import re
import seaborn as sns
import math
import matplotlib.pyplot as plt
import squarify  # pip install squarify (algorithm for treemap)
from functools import partial
from collections import Counter, OrderedDict
from itertools import groupby, permutations
import pandas as pd
import util
from copy import deepcopy
import numpy as np
from pprint import pprint
from pygal.style import CleanStyle, DefaultStyle

# from iaa_nugget_metrics import AgreementStudy, score_document_ere

pd.option_context("display.max_rows", None, "display.max_columns", None)


def count_no_participants_defined(event_list):
    cnt = sum(1 for ev in event_list if not ev.participants)
    total = len(event_list)
    return (cnt, total, round(100 * float(cnt) / total, 2))


def check_role_in_participants(event, role):
    all_participants = []
    if event.participants is not None:
        all_participants.extend(event.participants)
    coref_participants = event.get_coref_attrib("participants")
    if coref_participants is not None:
        all_participants.extend(coref_participants)
    return any(p.role == role for p in all_participants)


def is_weakly_realized(event):
    # is strongly realized if it has any arguments
    if event.participants or event.fillers or event.coreferents:
        return False
    # or if it has no coreferent events by recursion
    elif event.coreferents:
        return any(is_weakly_realized(coref_event) for coref_event in event.coreferents)
    else:
        return True


def group_and_process(l, group_key, process_func):
    l_sorted = sorted(l, key=group_key)
    for k, g in groupby(l_sorted, key=group_key):
        g = list(g)
        yield k, process_func(g)


iaa_ids = [
    "aapl14_iphone-x-s-dangerous-choice-of-market-share-or-profit.txt",
    "aapl15_here-s-how-apple-gets-to-a-2-trillion-market-value.txt",
    "aapl16_apple-s-app-store-generated-over-11-billion-in-revenue-for-th.txt",
    "amzn12_is-amazon-getting-into-the-pharmacy-business-this-is-what-you.txt",
    "amzn13_five-reasons-amazon-can-reach-1500.txt",
    "amzn14_amazon-sold-more-echo-dots-than-any-other-item-over-the-holidays.txt",
    "ba14_boeing-s-low-altitude-bid.txt",
    "ba15_should-boeing-buy-ge-aviation.txt",
    "ba16_boeing-s-stock-contributes-about-10-of-the-dow-s-1030-point.txt",
    "bac04_bank-of-america-earnings-hurt-by-tax-related-charge.txt",
    "bac05_bofa-includes-bitcoin-trust-in-broader-ban-on-investments.txt",
    "bac06_bank-of-america-hires-law-firm-to-help-probe-292-million-loss.txt",
    "cvx04_strong-crude-oil-no-help-for-chevron-exxon-mobil.txt",
    "cvx05_chevron-s-10-k-puts-the-permian-on-a-pedestal.txt",
    "cvx06_chevron-s-debt-fell-in-4q17-what-to-expect-in-2018.txt",
    "duk05_duke-energy-says-some-customers-may-be-affected-by-data-breach.txt",
    "duk06_like-many-of-its-peers-duk-is-trading-in-the-oversold-zone.txt",
    "duk07_duke-energy-stock-is-at-its-most-oversold-level-in-5-years.txt",
    "f13_ford-rolls-out-a-hot-rod-suv-as-drivers-abandon-performance-cars.txt",
    "f14_ford-is-the-next-ge-and-shorts-should-be-salivating.txt",
    "f15_ford-is-at-a-crossroad-of-danger-and-opportunity-in-china.txt",
    "jnj04_johnson-johnson-earnings-when-strong-is-nt-strong-enough.txt",
    "jnj05_where-s-the-tylenol-jj-disappoints-and-frustrates.txt",
    "jnj06_what-to-expect-from-johnson-johnson-in-2018.txt",
    "nem04_analyst-insight-is-newmont-mining-warming-up-for-a-good-2018.txt",
    "nem05_newmont-barrick-race-for-top-gold-crown-comes-down-to-a-decimal.txt",
    "nem06_newmont-mining-is-investors-gold-stock-to-buy.txt",
    "wmt05_walmart-stock-nears-key-support-after-earnings-miss.txt",
    "wmt06_goldman-expects-wal-mart-s-fortunes-to-improve-alongside-the-co.txt",
    "wmt07_walmart-s-meal-kits-are-not-the-solution-to-fight-amazon.txt",
]


def median_index(l):
    avg = sum(l) / len(l)
    dist = [abs(x - avg) for x in l]
    idx = dist.index(min(dist))
    return idx


def get_percentage_counter(counter):

    n = sum(counter.values())
    return {k: {"pct": round(100.0 * v / n, 2), "n": v} for k, v in counter.items()}


def select_redundant_annotated_doc(docs, method="best_tuple_score"):
    """
    From a list of the same source document with different annotations, select one annotated document.

    :param docs: list of annotation documents.
    :param method: Method for selecting annotation document.
        "best_tuple_score": score docs pairwise on ERE nugget score, select highest scorers.
        "most_events": largest unit count document is
        "median_events": median unit count
    :return: doc_selected: selected document
    """

    if method == "most_events":
        docs.sort(key=lambda x: len(x.events), reverse=True)
        cnt = {d.annotator_id: len(d.events) for d in docs}
        doc_selected = max(docs, key=lambda x: len(x.events))
    elif method == "median_events":
        docs.sort(key=lambda x: len(x.events), reverse=True)
        cnt = {d.annotator_id: len(d.events) for d in docs}
        doc_selected = docs[median_index([float(len(d.events)) for d in docs])]
    elif method == "best_tuple_score":
        for ref, gold in permutations(docs, 2):
            results = score_document_ere(ref, gold)
            #
            #
            pass

    print(
        f"{doc_selected.title} selected {doc_selected.annotator_id.upper()} by {method} {cnt}."
    )

    return doc_selected


def clean_project(proj):
    """
    Clean the project from empty and redundant docs to obtain the final corpus.
    Procedure is as follows:
    1. Remove documents without annotations: these are an artifact of WebAnno monitoring
    2.
    3.
    :param proj:
    :return:
    """
    # 1. check documents with no annotations
    unclean_len = len(proj.annotation_documents)
    proj.annotation_documents = [d for d in proj.annotation_documents if d.events]
    clean_len = len(proj.annotation_documents)
    print(
        f"Removed {unclean_len - clean_len} silver-standard docs without unit annotations. {unclean_len} remaining."
    )

    # # manual check double titles (was an issue with opening documents to annotators in WebAnno interfaces)
    # # title_cnt = Counter("".join(d.title.split("_")[1:]) for d in sent_proj.annotation_documents)
    # title_cnt = Counter(d.title for d in sent_proj.annotation_documents)
    # title_cnt = {k: v for k, v in title_cnt.items() if v > 1} # remove singles because not problematic
    # collect these double docs
    keep_docs = []
    single_annot_docs = (
        []
    )  # for returning when manually correcting: we avoid manually correcting these until final selection method is decided.
    for title, docgroup in groupby(proj.annotation_documents, key=lambda x: x.title):
        docs = list(docgroup)
        if len(docs) > 1:
            selected_doc = select_redundant_annotated_doc(
                docs, method="best_tuple_score"
            )
            keep_docs.append(selected_doc)

        else:
            keep_docs.append(docs[0])
            single_annot_docs.append(docs[0])
    print(
        f"Removed {clean_len - len(keep_docs)} duplicate annotated docs by keeping docs with most events."
    )
    proj.annotation_documents_clean = keep_docs
    proj.single_annotator_documents = single_annot_docs

    return keep_docs


def clean_events(evs):
    # evs_to_clean = [deepcopy(ev) for ev in evs]
    evs_to_clean = evs
    type_replace = {"CapitalReturns": "Dividend", "FinancialResult": "FinancialReport"}
    clean_evs = []

    for ev in evs_to_clean:
        # TODO replace changed subtypes
        if ev.event_type is not None:  # none types not included
            if ev.event_type in type_replace:  # replace changed types
                print(f"WRONG TYPE FOUND: {ev.event_type} {ev.document_title}")
                ev.event_type = type_replace[ev.event_type]
            if ev.event_subtype is None:  # replace none subtype by other
                ev.event_subtype = "Other"
            # # remove macroecon zonder participants
            # if not (ev.event_type == "Macroeconomics" and not check_role_in_participants(ev, "AffectedCompany")):
            #     clean_evs.append(ev)
            clean_evs.append(ev)

    return clean_evs


def collect_event_attribute(events, attribute_name):
    """

    :param unit:
    :param attr:
    :return:
    """
    vals = []
    for event in events:
        if getattr(event, attribute_name):
            for val in getattr(event, attribute_name):
                if val not in vals:
                    val.in_event = event
                    vals.append(val)
    return vals


def plot_type_treemap_interactive(type_df, fp="type_treemap_pygal.pdf"):
    # type treemap
    style = DefaultStyle(
        legend_font_size=12,
        tooltip_font_size=12,
    )
    treemap = pygal.Treemap(style=style, margin=0)
    treemap.title = "Event Type"

    for idx, row in type_df.iterrows():
        treemap.add(row.name, [row["pct"]])

    treemap.render_to_file(fp, print_values=False)


def write_participant_stats(all_events_clean):

    participants = collect_event_attribute(all_events_clean, "participants")
    df_participants = pd.DataFrame(
        {
            "participant_role": [p.role for p in participants],
            "on_typesubtype": [
                f"{p.in_event.event_type}.{p.in_event.event_subtype}"
                for p in participants
            ],
            "on_type": [p.in_event.event_type for p in participants],
        }
    )

    df_participants["id_mainsub"] = (
        df_participants["participant_role"].map(str)
        + "."
        + df_participants["on_typesubtype"].map(str)
    )
    df_participants["id_main"] = (
        df_participants["participant_role"].map(str)
        + "."
        + df_participants["on_type"].map(str)
    )

    # participant ratios on main type
    part_on_main_cnts = df_participants["id_main"].value_counts().to_dict()
    maintype_cnts = df_participants["on_type"].value_counts().to_dict()
    main_part_ratio = {}
    for k, v in part_on_main_cnts.items():
        k_maintype = k.split(".")[1]
        main_part_ratio[k] = round(100 * v / maintype_cnts[k_maintype], 2)

    df_participant_type_freq = pd.DataFrame(
        {"n/n_type": main_part_ratio, "n": part_on_main_cnts}
    ).sort_values(by=["n/n_type"])
    print(df_participant_type_freq)

    # participant ratios on subtypes
    part_on_mainsub_cnts = df_participants["id_mainsub"].value_counts().to_dict()
    mainsubtype_cnts = df_participants["on_typesubtype"].value_counts().to_dict()
    mainsub_part_ratio = {}
    for k, v in part_on_mainsub_cnts.items():
        k_mainsubtype = ".".join(k.split(".")[1:])
        mainsub_part_ratio[k] = round(100 * v / mainsubtype_cnts[k_mainsubtype], 2)

    df_participant_subtype_freq = pd.DataFrame(
        {"n/n_type.subtype": mainsub_part_ratio, "n": part_on_mainsub_cnts}
    ).sort_values(by=["n/n_type.subtype"])
    print(df_participant_subtype_freq)


def plot_type_treemap_matplot(type_df, fp="type_treemap_matplot.pdf"):

    type_df = type_df.rename(index={"Merger/Acquisition": "Merger/Acq."})
    type_df = type_df.drop(labels=["None"], axis=0)
    type_df = type_df.sort_values("n", ascending=True)

    type_df["label"] = type_df.apply(
        lambda x: r"$\bf{"
        + x.name
        + "}$"
        + f"\n{x['pct']:.1f}% (n={x['n'].astype('int')})",
        axis=1,
    )

    print(type_df)

    figsize = [10, 5.63]
    plt.rcParams["figure.figsize"] = figsize
    cmap = plt.get_cmap("tab20", lut=len(type_df.index))
    # Change color
    fig = plt.figure(figsize=figsize, dpi=300)
    squarify.plot(
        sizes=type_df["n"],
        label=type_df["label"],
        color=cmap.colors,
        alpha=0.4,
        figure=fig,
        pad=True,
    )
    plt.title(
        "Distribution of unit categories in SENTiVENT English corpus.",
        fontsize=12,
        figure=fig,
    )
    plt.axis("off")
    plt.show()
    fig.savefig(fp)


def compute_lexical_richness(
    events, by=["event_type"], extent=["discontiguous_triggers"], preproc=None
):
    """
    Compute lexical richness measures of unit attributes.
    event_type extracts the mention tokens

    :return:
    :param events: list of Event objects
    :param by: Group metric by attribute name. Used for grouping by event_type or subtype
    :param extent: Extent of the text getter functions on Event. Default: Full even trigger with discont.,
    :param preproc: list of preprocessing functions that take a string of text as input.
    :return:
    """
    from lexicalrichness import LexicalRichness

    print(
        f"Computing lexical richness of {str(extent).upper()} grouped by {str(by).upper()} with preprocessing: {str(preproc)}"
    )
    # collect text by attribute
    all_text = {}
    for attrib_name, g in groupby(
        events, key=lambda x: (getattr(x, attrib_n) for attrib_n in by)
    ):
        attrib_name = ".".join(str(attrib_name))

        for event in g:
            text = event.get_extent_text(extent=extent)
            if preproc:
                for preproc_func in preproc:
                    text = preproc_func(text)
            all_text.setdefault(attrib_name, []).append(text)

    # compute lexical diversity by attribute
    d = []
    for attrib_name, text in all_text.items():
        # This was a bad idea because mention TTR is nearly always 1.
        # # mean mention type-token ratio: variant of mean segment ttr (Johnsson 1944)
        # # instead of to_fix segments: annotation mentions
        # mention_ttr = [LexicalRichness(t).ttr for t in text]
        # mmttr = sum(mention_ttr) / len(text)
        # print(mention_ttr)
        # print(mmttr)

        # Lexical entropy
        p, lns = Counter(text), float(len(text))
        entropy = -sum(count / lns * math.log(count / lns, 2) for count in p.values())

        # metrics on all mentions together
        text = " ".join(text)
        lr = LexicalRichness(text)

        d.append(
            {
                "annotation_type": attrib_name,
                # "Mean mention TTR": mmttr, # this was a bad idea of mine
                "cttr": lr.cttr,
                "entropy": entropy,
                "dugast": lr.Dugast,
                "type_count": lr.terms,
                "token_count": lr.words,
                "herdan": lr.Herdan,
                "somers": lr.Summer,
                "maas": lr.Maas,  #  low sensivitty
                "ttr": lr.ttr,
                "rttr": lr.rttr,
                "mtld": lr.mtld(threshold=0.72),  # length correct,  mid sensivitty
                "msttr": lr.msttr(segment_window=25),  # length correct, mid sensivity
                "mattr": lr.mattr(window_size=25),  # length correct, mid sensivitty
                "hdd": lr.hdd(draws=42),  # length correct, high sensitivity
            }
        )

    df_lr = pd.DataFrame(d)
    # invert Maas for plotting
    df_lr["maas_inv"] = df_lr["maas"] * -1.0

    rec_metrics = ["maas", "hdd", "mtld"]  # recommended metrics in McCarthy 2010
    # rank
    df_lr = util.rank_dataframe_column(
        df_lr, ascending=False
    )  # add rank column for easy comparison
    df_lr["maas_rank"] = (
        df_lr["maas"].rank().astype(int)
    )  # Maas is inverted, lower score is more richness
    df_lr = df_lr.drop(
        labels=["annotation_type_rank"], axis=1
    )  # no need for index column ranking

    # nicer output
    df_lr = df_lr.sort_index(axis=1)  # sort columns alphabetically
    rank_cols = [c for c in df_lr if "_rank" in c and "_count" not in c]
    df_lr["rank_all"] = (
        df_lr[rank_cols].sum(axis=1).rank().astype(int)
    )  # sum every metric rank and rank inversely
    df_lr["rank_maas_hdd_mtld"] = (
        df_lr[[m + "_rank" for m in rec_metrics]].sum(axis=1).rank().astype(int)
    )  # combine recommended metrics
    df_lr = df_lr.set_index("annotation_type")
    df_lr = df_lr.sort_values(
        by="rank_maas_hdd_mtld"
    )  # sort values by conbination of recommended metrics in McCarthy 2010
    return df_lr


def plot_lexical_richness(
    lr_df,
    plot_metrics_as=OrderedDict(
        [
            ("hdd", "HDD"),
            ("maas_inv", "Maas (inverted)"),
            ("mtld", "MTLD"),
            ("entropy", "Entropy"),
        ]
    ),
    plot_name="lexical_richness.pdf",
):
    """
    Make the barplot for the lexical richness Dataframe. The columns to plot are set by plot_metric_as.
    :param lr_df: Dataframe contianing metrics
    :param plot_metrics_as: Dict containing which metrics to plot, how they should be renamed and in which order.
    :param plot_name: filename suffix for the plot
    :return: None, plot saved to file
    """
    # keep only relevant metric columns and rename
    lr_df = lr_df[list(plot_metrics_as.keys())]
    lr_df = lr_df.rename(columns=plot_metrics_as)
    lr_df.index.names = ["Event type"]
    # make plot and save
    # df_lr_plot.plot(subplots=True, layout=(df_lr_plot.shape[1], 1), sharex=True,
    #                 figsize=(7, 1.25 * df_lr_plot.shape[1]), marker=".")
    lr_df = lr_df.sort_values(by=list(plot_metrics_as.values()))
    lr_df.plot(kind="bar", sharex=True, figsize=(7, 1.25 * lr_df.shape[1]))
    labels = list(lr_df.index.values)
    ticks = list(range(len(labels)))
    plt.xticks(ticks=ticks, labels=labels, rotation=75)
    plt.savefig(f"lexicalrichness-{plot_name}.pdf", bbox_inches="tight")
    plt.show()

    # mean normalized plot
    lr_df_norm = (lr_df - lr_df.mean()) / lr_df.std()  # mean normalize
    lr_df_norm = lr_df_norm.sort_values(by=list(plot_metrics_as.values()))
    lr_df_norm.plot(kind="bar", sharex=True, figsize=(7, 1.25 * lr_df_norm.shape[1]))
    labels = list(lr_df_norm.index.values)
    ticks = list(range(len(labels)))
    plt.xticks(ticks=ticks, labels=labels, rotation=75)
    plt.savefig(f"lexicalrichness-{plot_name}-meannormalized.pdf", bbox_inches="tight")
    plt.show()


def compute_plot_lexical_richness(events):
    """
    compute lexical richness in types
    :param events:
    :return:
    """
    # set which metrics to be plotted, in order of sorting in plot
    # Maas, HDD, MTLD are recommended metrics in McCarthy 2010
    plot_metrics = OrderedDict(
        [
            ("hdd", "HDD"),
            ("maas_inv", "Maas (inverted)"),
            ("mtld", "MTLD"),
            ("entropy", "Entropy"),
        ]
    )
    # for unit trigger only
    df_lr_trigger = compute_lexical_richness(
        events,
        by=["event_type"],
        extent=["discontiguous_triggers"],
        preproc=[str.lower, util.filter_stopwords, util.stem_english],
    )
    df_lr_trigger.to_csv("lexical_richness_trigger_stemmed.csv")
    plot_lexical_richness(
        df_lr_trigger,
        plot_metrics_as=plot_metrics,
        plot_name="trigger",
    )

    # make full nugget lexical diversity plot
    df_lr_nugget = compute_lexical_richness(
        events,
        by=["event_type"],
        extent=["discontiguous_triggers", "participants", "fillers"],
        preproc=[str.lower, util.filter_stopwords, util.stem_english],
    )
    df_lr_nugget.to_csv("lexical_richness_trigger_part_fill_stemmed.csv")
    plot_lexical_richness(
        df_lr_nugget,
        plot_metrics_as=plot_metrics,
        plot_name="nugget-trigger-part-fill",
    )

    # TODO make sentence plot

    # # make joint plot (probably don't use this because scales are way off)
    # df_lr_joint = df_lr_trigger.join(
    #     df_lr_nugget, lsuffix="_trigger", rsuffix="_nugget"
    # )
    # plot_metrics = OrderedDict(
    #     [
    #         ("hdd_trigger", "HDD (trigger)"),
    #         ("maas_trigger", "Maas  (trigger)"),
    #         ("mtld_trigger", "MTLD  (trigger)"),
    #         ("entropy_trigger", "Entropy (trigger)"),
    #         ("hdd_nugget", "HDD (nugget)"),
    #         ("maas_nugget", "Maas (nugget)"),
    #         ("mtld_nugget", "MTLD (nugget)"),
    #         ("entropy_nugget", "Entropy (nugget)"),
    #     ]
    # )
    # plot_lexical_richness(
    #     df_lr_joint, plot_metrics_as=plot_metrics, plot_name="trigger+nugget"
    # )


if __name__ == "__main__":

    # This was for analysis during cleaning and before adjucation: we now have a cleaned canonical corpus
    # # opt_dirp = "sentivent_en_webanno_project_my_obj.pickle"
    # opt_dirp = "sentivent_en_webanno_correction.pickle"
    # exclude_gilles = lambda x: "anno" in Path(x.path).stem
    #
    # with open(opt_dirp, "rb") as project_in:
    #     iaa_project = pickle.load(project_in)

    # clean the corpus of redundantly annotated docs
    # single_annotated_docs = clean_project(iaa_project)
    proj = parse_project(settings.MASTER_DIRP_BEFORE_SEPT, from_scratch=False)
    # sent_proj = parse_project(settings.CLEAN_XMI_DIRP)
    all_docs = proj.annotation_documents

    # get general corpus stats: TODO add counts for multi-word triggers as in Liu 2015
    attribs = [
        "events",
        "sentences",
        "tokens",
        "participants",
        "fillers",
        "discontiguous_triggers",
        "canonical_referents",
        "coreferent_event_xmidata",
    ]
    # compute avg attrib per doc + total
    avg_total = {
        attrib: count_avg(all_docs, attrib, return_counts=True) for attrib in attribs
    }
    avg_dev = {
        attrib: count_avg(proj.dev, attrib, return_counts=True) for attrib in attribs
    }
    avg_test = {
        attrib: count_avg(proj.test, attrib, return_counts=True) for attrib in attribs
    }
    general_corpus_stats_df = pd.DataFrame(
        [x[1] for x in avg_total.values()], index=avg_total.keys()
    )
    general_corpus_stats_df.loc["documents"] = len(all_docs)
    general_corpus_stats_df = general_corpus_stats_df.rename(
        index={
            "canonical_referents": "Canonical referent link",
            "coreferent_event_xmidata": "Co-reference links",
            "discontiguous_triggers": "Discontinuous triggers",
        }
    )
    print(
        general_corpus_stats_df.to_latex(
            caption="Basic corpus statistics.", label="tab:basicstats"
        )
    )

    all_events = []
    for d in all_docs:
        for ev in d.events:
            all_events.append(ev)

    # plot lexical richness
    # compute_plot_lexical_richness(all_events)

    # count subtype
    subtype_count = Counter(
        f"{ev.event_type}.{ev.event_subtype}" for ev in all_events if ev.event_subtype
    )

    # count weakly realized events
    weak_events = [ev for ev in all_events if is_weakly_realized(ev)]
    weak_docs = []
    for title, evs in groupby(
        sorted(weak_events, key=lambda x: x.document_title),
        key=lambda x: x.document_title,
    ):
        evs = list(evs)
        weak_docs.append((title, len(evs), evs))
    weak_docs.sort(key=lambda x: x[1], reverse=True)

    weak_doc_types = []
    for titletype, evs in groupby(
        sorted(weak_events, key=lambda x: f"{x.document_title}-{x.event_type}"),
        key=lambda x: f"{x.document_title}-{x.event_type}",
    ):
        evs = list(evs)
        weak_doc_types.append((titletype, len(evs), evs))
    weak_doc_types.sort(key=lambda x: x[1], reverse=True)

    weak_cnt = len(weak_events)
    weak_types = Counter(ev.event_type for ev in weak_events)

    # count unit subtypes
    avg_subtype_count = get_percentage_counter(
        Counter(
            f"{ev.event_type}.{ev.event_subtype}"
            if ev.event_subtype
            else f"{ev.event_type}.yunspecified"
            for ev in all_events
        )
    )
    subtype_index = [tuple(k.split(".")) for k in avg_subtype_count.keys()]
    multindex = pd.MultiIndex.from_tuples(subtype_index, names=["Type", "Subtype"])
    subtype_df = pd.DataFrame(avg_subtype_count.values(), index=multindex).sort_index()
    subtype_df["n"] = subtype_df["n"].astype(int)
    print("Event subtypes", avg_subtype_count)
    subtype_df.to_csv("subtype_data.csv")

    type_df = subtype_df.sum(level="Type")

    # add total subtype count to subtype_df
    for type, subtype_g in groupby(list(subtype_df.index), key=lambda x: x[0]):
        if len(list(subtype_g)) > 1:  # if type has subtypes: add totals
            subtype_df.loc[(type, "ztotal"), :] = type_df.loc[type]
    subtype_df = subtype_df.sort_index()
    subtype_df["n"] = subtype_df["n"].astype(int)
    subtype_latex_table = subtype_df.to_latex(
        multirow=True,
        caption="Event type and subtype counts in corpus.",
        label="tab:eventtypesubtype",
        float_format="%.1f",
    )
    # add cdashline to total cell
    subtype_latex_table = re.sub(
        r"^(\s+\&\s)ztotal",
        r"\\cdashline{2-4}\n\1total",
        subtype_latex_table,
        0,
        re.MULTILINE,
    )
    # remove yunspecified to unspec
    subtype_latex_table = re.sub(
        r"(^(\w|\/)+\s\&\s)yunspecified", r"\1", subtype_latex_table, 0, re.MULTILINE
    )
    subtype_latex_table = re.sub(
        "yunspecified", "unspecified", subtype_latex_table, 0, re.MULTILINE
    )
    # add cline
    subtype_latex_table = re.sub(
        r"(\\\\$\n)(\w+(\/\w+)?\s\&\s+\&|\\multirow)",
        r"\1\\cline{1-4}\n\2",
        subtype_latex_table,
        0,
        re.MULTILINE,
    )
    print(subtype_latex_table)

    print(
        type_df.to_latex(
            caption="Event type counts in corpus.",
            label="tab:eventtype",
            float_format="%.1f",
        )
    )

    def get_company_info(document_title, column, company_df):
        if not document_title[:1].isdigit():
            tickersymbol = document_title.split("_")[0][:-2]
            company_info_row = company_df.loc[
                company_df["tickersymbol"] == tickersymbol
            ]
            val = company_info_row[column].tolist()[0]
            return val
        else:
            return "Unresolved"

    comp_cnt = Counter(ev.document_title.split("_")[0][:-2] for ev in all_events)
    print(comp_cnt, len(comp_cnt))
    companies_df = pd.read_csv("corpus_companies.tsv", sep="\t", index_col=False)
    companies_df["tickersymbol"] = companies_df["corpussymbol"].str.lower()
    # count of events and docs per company
    # create document dataframe
    df_documents = pd.DataFrame(
        {
            "document_title": [d.title for d in all_docs],
            "company": [
                get_company_info(d.title, "security", companies_df) for d in all_docs
            ],
            "industry": [
                get_company_info(d.title, "industry", companies_df) for d in all_docs
            ],
            "subindustry": [
                get_company_info(d.title, "subindustry", companies_df) for d in all_docs
            ],
        }
    )
    # create unit dataframe
    df_events = pd.DataFrame(
        {
            "event_type": [ev.event_type for ev in all_events],
            "event_subtype": [ev.event_subtype for ev in all_events],
            "annotator_id": [ev.annotator_id for ev in all_events],
            "document_title": [ev.document_title for ev in all_events],
            "company": [
                get_company_info(ev.document_title, "security", companies_df)
                for ev in all_events
            ],
            # actually to many computations here use groupby to group tickers than look up once for company info
            "industry": [
                get_company_info(ev.document_title, "industry", companies_df)
                for ev in all_events
            ],
            "subindustry": [
                get_company_info(ev.document_title, "subindustry", companies_df)
                for ev in all_events
            ],
        }
    )

    # count events and docs per industry
    df_industry_freq = pd.DataFrame(
        {
            "doc_target_freq": {
                "Consumer Discretionary": 20.00,
                "Consumer Staples": 10.00,
                "Energy": 10.00,
                "Financials": 10.00,
                "Health Care": 10.00,
                "Industrials": 10.00,
                "Information Technology": 20.00,
                "Materials": 3.33,
                "Telecommunication Services": 3.33,
                "Utilities": 3.33,
            },
        }
    )
    df_industry_freq["doc_counts"] = df_documents["industry"].value_counts()
    df_industry_freq["doc_freq"] = (
        df_documents["industry"].value_counts(normalize=True) * 100
    )
    df_industry_freq["doc_target_delta"] = (
        df_industry_freq["doc_target_freq"] - df_industry_freq["doc_freq"]
    )
    df_industry_freq["event_counts"] = df_events["industry"].value_counts()
    df_industry_freq["event_freq"] = (
        df_events["industry"].value_counts(normalize=True) * 100
    )
    # # count of events and docs per company
    companies_df = companies_df.set_index("security").sort_index()
    companies_df = companies_df.join(df_documents["company"].value_counts())
    print(companies_df)

    print(companies_df[["industry", "corpussymbol", "company"]].to_latex())

    print(df_industry_freq)

    # get participant frequencies
    write_participant_stats(all_events)

    avg_type_count = get_percentage_counter(Counter(ev.event_type for ev in all_events))
    print("Event types: ", avg_type_count)

    plot_type_treemap_matplot(type_df)

    # create a list of unit annotations that have changed and fix them

    event_getter = {
        "event_type": [
            "CapitalReturns",
            "FinancialResult",
        ]
    }
    edits = [
        ev
        for ev in all_events
        if ev.event_type
        in [
            "CapitalReturns",
            "FinancialResult",
        ]
    ]
    gkey = lambda x: (x.document_title, x.annotator_id)
    doc_replace_cnt = [
        (title, len(list(g))) for title, g in groupby(sorted(edits, key=gkey), key=gkey)
    ]
    for title, cnt in sorted(doc_replace_cnt, key=lambda x: x[1], reverse=True):
        print(title, cnt)

    # events with no participants
    cnt_no_participants = sum(1 for ev in all_events if not ev.participants)
    print(
        f"{cnt_no_participants}/{len(all_events)} ({round(100*float(cnt_no_participants)/len(all_events), 2)}%) unit without participants."
    )
    group_key = lambda x: x.annotator_id
    all_events_sorted = sorted(all_events, key=group_key)
    for anid, evs in groupby(all_events_sorted, key=group_key):
        evs = list(evs)
        cnt_no_participants = sum(1 for ev in evs if not ev.participants)
        print(
            f"\t{anid} {cnt_no_participants}/{len(evs)} ({round(100 * float(cnt_no_participants) / len(evs),2)}%)"
        )

    # parse histoplot of doc_length in sentences and words over amount of unit annos
    df_event_cnt = pd.DataFrame(
        {
            "title": [doc.title for doc in all_docs],
            "event_count": [len(doc.events) for doc in all_docs],
            "token_count": [len(doc.tokens) for doc in all_docs],
            "sentence_count": [len(doc.sentences) for doc in all_docs],
        }
    )

    sns.set_style("darkgrid")

    sns.regplot(
        x="event_count", y="sentence_count", data=df_event_cnt, x_estimator=np.mean
    )
    plt.show()

    sns.regplot(
        x="event_count",
        y="sentence_count",
        data=df_event_cnt,
        x_estimator=np.mean,
        logx=True,
        truncate=True,
    )
    plt.show()

    sns.regplot(
        x="event_count", y="token_count", data=df_event_cnt, x_estimator=np.mean
    )
    plt.show()

    sns.regplot(
        x="event_count",
        y="token_count",
        data=df_event_cnt,
        x_estimator=np.mean,
        logx=True,
        truncate=True,
    )
    plt.show()

    sns.distplot(df_event_cnt["event_count"])
    plt.show()

    # TODO examine correlation of event_type and company

    # TODO examine correlation of event_type and industry

    # TODO examine correlation of event_type with event_type

    compute_plot_lexical_richness(all_events)
