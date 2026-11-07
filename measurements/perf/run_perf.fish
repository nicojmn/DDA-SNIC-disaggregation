#!/usr/bin/env fish

argparse e/engine= n/nvme= r/rw= s/size= d/duration= o/output_dir= f/freq= c/cpu= p/pci= m/mixed_params= -- $argv
or exit 1

# Set defaults
set engine libaio
set duration 300
set freq 999
set cpu 0
set output_dir "."
set mixed_params ""
set pci_address ""

if set -q _flag_engine
    set engine $_flag_engine
end

if set -q _flag_nvme
    set nvme $_flag_nvme
end

if set -q _flag_rw
    set rw $_flag_rw
else
    echo "rw flag is mandatory"
    exit 1
end

if set -q _flag_size
    if not string match -qr '^[0-9]+$' -- $_flag_size
        echo "Error: size must be an integer"
        exit 1
    end
    set size $_flag_size
else
    echo "Error: size flag is mandatory"
    exit 1
end

if set -q _flag_duration
    set duration $_flag_duration
end

if set -q _flag_output_dir
    mkdir -p $_flag_output_dir
    set output_dir $_flag_output_dir
end

if set -q _flag_freq
    if test $_flag_freq -lt 900
        echo "Error: freq is too small"
        exit 1
    end
    set freq $_flag_freq
end

if set -q _flag_cpu
    set cpu $_flag_cpu
end

if set -q _flag_pci
    set pci_address $_flag_pci
end

if set -q _flag_mixed_params
    set mixed_params $_flag_mixed_params
end

set timestamp (date +%Y%m%d_%H%M%S)
set perf_basename "$output_dir/perf_$engine_$size_$rw_$timestamp"
echo "Writing to: $perf_basename\[.data|.svg|.script\]"

if test "$engine" = spdk_bdev
    # Check if nvme flag was provided
    if not set -q nvme
        echo "Error: nvme flag required for spdk_bdev engine"
        exit 1
    end

    if test "$pci_address" = ""
        echo "Error: pci flag required for spdk_bdev engine"
        exit 1
    end

    if test -b "/dev/$nvme"
        set nvme_found ""
        for dev in /dev/nvme0n*
            test -b "$dev"; or continue
            set sysfs_link (readlink -f /sys/class/block/(basename "$dev") 2>/dev/null)
            if echo "$sysfs_link" | grep -q "$pci_address"
                set nvme_found (basename "$dev")
                echo "Found NVMe device: $nvme_found at PCI $pci_address"
                break
            end
        end

        if test -z "$nvme_found"
            echo "ERROR: Could not find NVMe device at PCI $pci_address"
            exit 1
        end

        env PCI_ALLOWED=$pci_address /etinfo/users/2021/njeanmenne/spdk/scripts/setup.sh
        while test -b "/dev/$nvme_found"
            echo "Waiting to bind SPDK ($nvme_found)..."
            sleep 1
        end
    end

    printf '%s\n' '{
  "subsystems": [
    {
      "subsystem": "bdev",
      "config": [
        {
          "method": "bdev_nvme_attach_controller",
          "params": {
            "name": "Nvme0",
            "trtype": "PCIe",
            "traddr": "'"$pci_address"'"
          }
        }
      ]
    }
  ]
}' >/tmp/benchmark-conf.json

    set fio_cmd env LD_PRELOAD=/etinfo/users/2021/njeanmenne/spdk/build/fio/spdk_bdev fio \
        --name=npf_spdk-fio_read \
        --ioengine=$engine \
        --spdk_json_conf=/tmp/benchmark-conf.json \
        --filename=Nvme0n1 \
        --direct=1 \
        --thread=1 \
        --overwrite=1 \
        --time_based=1 \
        --runtime=$duration \
        --ramp_time=30 \
        --percentile_list=99:99.9:99.99 \
        --rw=$rw \
        --bs=4K \
        --iodepth=64 \
        --size=$size\M \
        --output-format=json
else
    set fio_cmd \
        fio \
        --name=perf_run_$timestamp \
        --ioengine=$engine \
        --filename=/dev/$nvme \
        --direct=1 \
        --thread=1 \
        --overwrite=1 \
        --rw=$rw \
        --bs=4K \
        --iodepth=64 \
        --size=$size\M \
        --ramp_time=10 \
        --runtime=$duration \
        --time_based \
        --output-format=json \
        --output="$perf_basename"_fio.json
end

sudo sysctl -q kernel.perf_event_paranoid=-1

sudo perf record -F $freq -g --call-graph dwarf -o "$perf_basename.data" -- $fio_cmd

if not set -q FLAMEGRAPH
    echo "Warning: FLAMEGRAPH environment variable not set"
    set FLAMEGRAPH ~/FlameGraph
end

sudo perf script -i "$perf_basename.data" | $FLAMEGRAPH/stackcollapse-perf.pl | $FLAMEGRAPH/flamegraph.pl --title "FIO ($engine) $rw with $size MB flame graph" >"$perf_basename.svg"

sudo perf script -i "$perf_basename.data" >"$perf_basename.script"
