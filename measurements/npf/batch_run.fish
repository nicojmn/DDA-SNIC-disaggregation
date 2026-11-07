#!/usr/bin/env fish

argparse c/cache m/mode= s/suffix= b/boilerplate-only -- $argv
or exit 1

set npf_file "$argv[1]"
set target_dir (dirname "$npf_file")
set formatted_name (string replace -a "/" "_" $target_dir)
set script_dir scripts

set cache
if set -q _flag_cache
    set cache --cache
end

if set -q _flag_mode
    set mode (string split " " "$_flag_mode")
else
    set mode read write randread randwrite rw randrw
end

if set -q _flag_suffix
    set title_suffix "$_flag_suffix"
end

function sed_mode -a m file
    sed -E -e "s/RW=[{][^}]*[}]/RW={$m}/g" \
        -e "s/spdk_bdev fio \[.*\] benchmark/spdk_bdev fio [$m] benchmark/g" \
        "$file" >""$script_dir"/run_"$formatted_name"_"$m".npf"
end

function run_npf_tests
    if not test -f "$npf_file"
        echo "Error: file '$npf_file' not found."
        return 1
    end

    for rw in $mode
        if test "$rw" = randread
            set graph_title "Random read"
            sed_mode "$rw" "$npf_file"
        else if test "$rw" = read
            set graph_title "Sequential read"
            sed_mode "$rw" "$npf_file"
        else if test "$rw" = randwrite
            set graph_title "Random write"
            sed_mode "$rw" "$npf_file"
        else if test "$rw" = write
            set graph_title "Sequential write"
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

        npf $cache --test ""$script_dir"/run_"$formatted_name"_"$rw".npf" --use-local $target_dir \
            --single-output "$target_dir/csv/$rw.csv" \
            --graph-title "$graph_title" \
            --graph-filename "$target_dir/graphs/$rw.pdf"
    end
end

if set -q _flag_boilerplate_only
    echo (set_color yellow) "Generating boilerplate npf only !"
else
    run_npf_tests
    exit 0
end
