from typing import cast, List
from ..fs.fuse import *
from ..fs.operation import *
from pandas import DataFrame
import numpy as np
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


def get_reads(o: Fuse) -> List[Read]:
    is_read = lambda op: type(op).__name__ == 'Read' # helps with jupyter autoreloading
    return cast(List[Read], list(filter(is_read, o.ops)))

def make_df(fuse: Fuse) -> DataFrame:
    l = fuse.ops_list
    df = DataFrame(l, columns=fuse.columns)

    if len(df) == 0:
        return df
    # df = df[df.kind != 'Prefetch']

    tss = df.timestamp.min()
    df.timestamp -= tss

    return df

def draw_reads(df: DataFrame, **kwargs):
    plt.close()
    plt.figure(figsize=(12, 8))
    if df.empty:
        print("No reads")
        return
    colors = { 'Prefetch': 'b', 'Hit': 'g', 'Miss': 'r' }
    for kind, color in colors.items():
        data = df[df.kind == kind]
        x = data.timestamp
        y = data.offset
        y = data.offset + data.length
        plt.plot((x,x), (y, y + data.length), c=color, label=kind)

    patches = [mpatches.Patch(color=color, label=kind) for kind, color in colors.items()]
    # plt.legend(handles=patches)
    plt.ylabel('KB read (offset..offset+length)')
    plt.show()

def draw_reads_all_files(df: DataFrame):
    plt.close()

    colors = { 'Prefetch': 'b', 'Hit': 'g', 'Miss': 'r' }

    files = list(set(df.filename))
    cols = int(len(files) / 4) + 1
    fig, axs = plt.subplots(cols, 4, figsize=(40,4 * cols))
    axs = axs.flatten()

    for f, ax in zip(files, axs):
        data = df[df.filename == f]
        if data.empty:
            continue
        x = data.timestamp
        y = data.offset
        y = data.end
        ax.plot((x,x), (y, y + data.length), c='r')
        ax.set_title(f)

        # patches = [mpatches.Patch(color=color, label=kind) for kind, color in colors.items()]
        # ax.legend(handles=patches)
        # ax.ylabel('KB read (offset..offset+length)')
        # ax.title(f)

def read_stats(df: DataFrame):
    print(df.groupby(df.kind).count())

def predictor_stats(df: DataFrame):
    counts = df.groupby(['source', 'hit']).size()
    reads = counts.loc['read']

    prefetch_len = len(df[df.source == 'prefetch']) or 1
    hit_rate = reads.get(True, 0) / reads.sum()
    prefetch_fingerprints = set(df[df.source == 'prefetch'].fingerprint)
    hits_fingerprints = set(df[(df.source == 'read') & (df.hit == True)].fingerprint)
    used_fingerprints = len(prefetch_fingerprints & hits_fingerprints)

    use_rate = used_fingerprints * 1.0 / prefetch_len

    # accuracy
    # A = take all prefetches
    prefetch_indexes = df[df.source == 'prefetch'].index
    # B = take all reads
    read_indexes = df[df.source != 'prefetch'].index
    # match A with B, so for each A.id we have min(B.id) where B.id > A.id
    prefetch_map = { i: None for i in prefetch_indexes }
    idx = 0
    for i in prefetch_indexes:
        while True:
            here = read_indexes[idx]
            if here > i:
                prefetch_map[i] = here
                break
            else:
                idx += 1

            if idx >= len(read_indexes):
                break

    accuracy = 0
    for p_id, r_id in prefetch_map.items():
        if not r_id:
            continue
        prefetch = df.loc[p_id]
        read = df.loc[r_id]
        same = prefetch.filename == read.filename and prefetch.offset == read.offset
        if same:
            accuracy += 1
    accuracy /= len(prefetch_map) or 1

    return {
        "hit_rate": hit_rate,
        "accuracy": accuracy,
        "use_rate": use_rate,
        "time_taken": df.timestamp.max(),
    }


def plot_stat_multibar(results: DataFrame, stat: str):
    import matplotlib.ticker as mtick
    names = {
        'hit_rate': 'Hit rate',
        'use_rate': 'Usage rate',
        'accuracy': 'Accuracy',
        'time_taken': 'Usage rate',
    }

    workers = list(set(results.worker))
    methods = list(set(results.method))
    X_axis = np.arange(len(workers))

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.grid(axis="y", zorder=0)
    ax.set_xticks(X_axis)
    ax.set_xticklabels(workers)
    ax.set_xlabel("Test application")
    ax.set_ylabel(names[stat])

    if 'rate' in stat:
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_yticks([0, 25,50, 75, 100])
        ax.set_ylim(0, 105)
    ax.set_title("")

    width = 0.16
    middle = (len(methods) - 1.0) * width / 2
    for i, method in enumerate(methods):
        data = results[(results.method == method)][['worker', stat]].set_index('worker').to_dict()[stat]
        mult = 100 if 'rate' in stat else 1
        data = [ mult * data[m] for m in workers]
        ax.bar(X_axis + width*i-middle, data, width, label = method, zorder=100)
    ax.legend(methods, bbox_to_anchor=(0, 1, 1, 0), loc="lower left", mode="expand", ncol=2)
