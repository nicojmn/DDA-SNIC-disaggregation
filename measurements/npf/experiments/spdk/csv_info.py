import argparse
import pandas as pd


def filter_dics(dict, keys=['SIZE', 'IODEPTH', 'y_BANDWIDTH']):
    return {k: dict[k] for k in keys if k in dict}
    
parser = argparse.ArgumentParser(description='Print the best throughput for a given csv file.')
parser.add_argument('csv_file', type=str, help='Path to the csv file containing the throughput results.')
parser.add_argument('info', type=str, help='Information to retrieve. Can be either "mean", "median", "max", or "min".') 
parser.add_argument('-s', '--size', type=int, help='Filter by SIZE (e.g., 10 for 10MB)', required=False)
parser.add_argument('-d', '--iodepth', type=int, help='Filter by IODEPTH (e.g., 16)', required=False)
args = parser.parse_args()
info = args.info.lower()
if info not in ['mean', 'median', 'max', 'min']:
    print("Invalid info type. Please choose from 'mean', 'median', 'max', or 'min'.")
    exit(1)


def B_to_GB(value):
    return round(value / (1000 ** 3), 2)


df = pd.read_csv(args.csv_file)


if args.size:
    df = df[df['SIZE'] == args.size]
if args.iodepth:
    df = df[df['IODEPTH'] == args.iodepth]

if df.empty:
    print("No data matching the specified criteria.")
    exit(1)

df_spdk = df[df['ENGINE'] == 'spdk_bdev']
df_fio = df[df['ENGINE'] == 'libaio']


if info == 'mean':
    info_spdk = df_spdk['y_BANDWIDTH'].mean()
    info_fio = df_fio['y_BANDWIDTH'].mean()
elif info == 'median':
    info_spdk = df_spdk['y_BANDWIDTH'].median()
    info_fio = df_fio['y_BANDWIDTH'].median()
elif info == 'max':
    info_spdk = df_spdk['y_BANDWIDTH'].max()
    info_fio = df_fio['y_BANDWIDTH'].max()
elif info == 'min':
    info_spdk = df_spdk['y_BANDWIDTH'].min()
    info_fio = df_fio['y_BANDWIDTH'].min()

if pd.notna(info_spdk):
    row_spdk = df_spdk.iloc[(df_spdk['y_BANDWIDTH'] - info_spdk).abs().argmin()]
    print(f"{info.capitalize()} throughput (SPDK) : {B_to_GB(info_spdk)} GB/s")
    print(f"Params for best {info} (SPDK): {filter_dics(row_spdk.to_dict())}")

if pd.notna(info_fio):
    row_fio = df_fio.iloc[(df_fio['y_BANDWIDTH'] - info_fio).abs().argmin()]
    print(f"{info.capitalize()} throughput (FIO) : {B_to_GB(info_fio)} GB/s")
    print(f"Params for best {info} (FIO): {filter_dics(row_fio.to_dict())}")
