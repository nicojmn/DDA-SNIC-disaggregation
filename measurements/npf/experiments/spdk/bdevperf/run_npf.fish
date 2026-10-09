#!/usr/bin/env fish

argparse c/cache m/mode= s/suffix= -- $argv
or exit 1

set npf_file "$argv[1]"
set target_dir (dirname $npf_file)

set cache
set title_suffix
# set extra_args
if set -q _flag_cache
    set cache --cache
end

if set -q _flag_mode
    set mode (string split " " "$_flag_mode")
else
    set mode read write randread randwrite rw randrw
end

if set -q _flag_suffix
    set title_suffix $_flag_suffix
end

# if set -q _flag_extra_args
#     set extra_args $_flag_extra_args
# end

function sed_mode -a m file
    sed -E -e "s/RW=[{][^}]*[}]/RW={$m}/g" \
        -e "s/bdevperf \[.*\] benchmark/spdk_bdev fio [$m] benchmark/g" \
        "$file" >"run.npf"
end

function run_npf_tests
    if not test -f "$npf_file"
        echo "Error: file '$npf_file' not found."
        return 1
    end

    for rw in $mode
        if test "$rw" = randread
            set graph_title "Random read throughput"
            sed_mode "$rw" "$npf_file"
        else if test "$rw" = read
            set graph_title "Sequential read throughput"
            sed_mode "$rw" "$npf_file"
        else if test "$rw" = randwrite
            set graph_title "Random write throughput"
            sed_mode "$rw" "$npf_file"
        else if test "$rw" = write
            set graph_title "Sequential write throughput"
            sed_mode "$rw" "$npf_file"
        else if test "$rw" = rw
            set graph_title "Sequential mixed read/write"
            sed_mode "$rw" "$npf_file"
        else if test "$rw" = randrw
            set graph_title "Random mixed read/write"
            sed_mode "$rw" "$npf_file"
        else
            echo (set_color red) "Unrecognized paramater : $rw"
            exit 1
        end

        if test -n "$title_suffix"
            set graph_title "$graph_title $title_suffix"
        end

        npf $cache --test "run.npf" --use-local $target_dir \
            --single-output "$target_dir/csv/$rw.csv" \
            --graph-title "$graph_title" \
            --graph-filename "$target_dir/graphs/$rw.pdf" # \
        # "$extra_args"
        rm "run.npf"
    end
end

run_npf_tests
