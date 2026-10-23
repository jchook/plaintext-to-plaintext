#!/usr/bin/env python3
"""Plot original payload bytes against generated cover bytes from saved trials."""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import statistics
import tempfile

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'p2p-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import StrMethodFormatter

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'runs/pilot-20261022/results.json'
DESTINATION = HERE / 'plots'
TEMPERATURES = ['0.8', '1.0', '1.2', '1.4', '1.6']
COLORS = ['#6d28d9', '#2563eb', '#0891b2', '#d97706', '#dc2626']
CASE_LABELS = {
    'key-message': 'short text', 'unicode': 'Unicode',
    'binary': 'binary', 'paragraph': 'paragraph',
}


def main():
    source_bytes = SOURCE.read_bytes()
    rows = json.loads(source_bytes)
    cells = defaultdict(list)
    points = []
    for row in rows:
        stats = row['encode']
        prefix = stats['opening_bytes'] + stats['separator_bytes']
        continuation = stats['cover_bytes'] - prefix
        assert continuation == stats['continuation_bytes']
        assert continuation == stats['payload_cover_bytes'] + stats['suffix_bytes']
        assert row['exact_bytes'] and row['decode']['authenticated']
        point = {
            'name': row['name'], 'case': row['case'],
            'temperature': row['temperature'], 'repetition': row['repetition'],
            'plaintext_bytes': stats['plaintext_bytes'],
            'packed_source_bytes': stats['packed_source_bytes'],
            'generated_stegotext_bytes': continuation,
            'excluded_opening_and_separator_bytes': prefix,
        }
        cells[(point['temperature'], point['case'])].append(point)
        points.append(point)
    assert len(points) == 40 and len(cells) == 20
    assert all(len(cell) == 2 for cell in cells.values())
    assert {p['excluded_opening_and_separator_bytes'] for p in points} == {358}

    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 11,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.labelcolor': '#253047', 'text.color': '#172033',
        'xtick.color': '#465269', 'ytick.color': '#465269',
        'svg.fonttype': 'none',
    })
    fig, ax = plt.subplots(figsize=(11.5, 7.8))
    fig.subplots_adjust(left=0.10, right=0.96, top=0.76, bottom=0.30)
    fig.text(0.10, 0.94, 'Plaintext length vs generated stegotext length',
             fontsize=20, weight='bold', ha='left')
    fig.text(0.10, 0.895, 'Supplied opening paragraph and separator excluded (358 bytes)',
             fontsize=12, color='#465269', ha='left')
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#e3e8ef', linewidth=0.8)
    ax.set_facecolor('#fbfcfe')
    means = []
    for temperature, color in zip(TEMPERATURES, COLORS):
        cases = sorted(CASE_LABELS, key=lambda case: cells[(temperature, case)][0]['plaintext_bytes'])
        for case in cases:
            cell = cells[(temperature, case)]
            x = cell[0]['plaintext_bytes']
            values = [p['generated_stegotext_bytes'] for p in cell]
            average = statistics.mean(values)
            ax.scatter([x] * len(values), values, color=color, s=19, alpha=0.60, zorder=3)
            ax.errorbar(x, average, yerr=[[average-min(values)], [max(values)-average]],
                        fmt='D', markersize=6, color=color, markeredgecolor='white',
                        markeredgewidth=0.7, capsize=5, elinewidth=1.5, zorder=4)
            means.append({'temperature': temperature, 'case': case,
                          'plaintext_bytes': x, 'mean_generated_stegotext_bytes': average,
                          'min_generated_stegotext_bytes': min(values),
                          'max_generated_stegotext_bytes': max(values), 'trials': len(cell)})

    ticks = sorted({(p['plaintext_bytes'], p['case']) for p in points})
    ax.set_xticks([x for x, _ in ticks], [f'{x}\n{CASE_LABELS[case]}' for x, case in ticks])
    ax.tick_params(axis='x', labelsize=10)
    ax.set_xlim(0, 255)
    ax.set_ylim(0, 4200)
    ax.set_xlabel('Original plaintext / payload length (bytes)', labelpad=14)
    ax.set_ylabel('Generated stegotext length (bytes)', labelpad=10)
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
    handles = [Line2D([], [], marker='D', linestyle='none', color=color,
                      markeredgecolor='white', markersize=7, label=temperature)
               for temperature, color in zip(TEMPERATURES, COLORS)]
    ax.legend(handles=handles, title='Temperature', ncol=5, frameon=False,
              loc='lower left', bbox_to_anchor=(-0.01, 1.015),
              columnspacing=2.1, handletextpad=0.4)
    fig.text(0.10, 0.115, 'Diamonds: means. Dots and vertical bars: the two trials and their range.',
             fontsize=10, color='#465269')
    fig.text(0.10, 0.078, 'Sentence endings are included. All 40 trials recovered the original bytes exactly.',
             fontsize=10, color='#465269')
    fig.text(0.10, 0.041, 'Different payloads are not a length-only scaling test: the 238-byte paragraph compresses to 49 bytes.',
             fontsize=10, color='#465269')
    DESTINATION.mkdir(exist_ok=True)
    stem = DESTINATION / 'plaintext-vs-stegotext'
    fig.savefig(stem.with_suffix('.png'), dpi=180, facecolor='white')
    fig.savefig(stem.with_suffix('.svg'), facecolor='white')
    plt.close(fig)
    stem.with_suffix('.json').write_text(json.dumps({
        'source': str(SOURCE.relative_to(HERE)),
        'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'x': 'Original plaintext/payload bytes, before lossless compression',
        'y': 'Full cover bytes minus supplied opening paragraph and separator',
        'sentence_completion_included': True,
        'points': points, 'means_and_ranges': means,
    }, indent=2) + '\n')
    print(stem.with_suffix('.png'))


if __name__ == '__main__':
    main()
