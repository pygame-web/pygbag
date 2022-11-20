import os
import sys
from pathlib import Path


"""
pngquant -f --ext -pygbag.png --quality 40 $(find|grep png$)

for wav in $(find |grep wav$)
do
    d=$(dirname "$wav")
    f=$(basename "$wav" .wav)
    ffmpeg -i "$wav" -ac 1 -r 22000 "$d/$f.ogg"
done

for mp3 in $(find |grep mp3$)
do
    d=$(dirname "$mp3")
    f=$(basename "$mp3" .mp3)
    ffmpeg -i "$mp3" -ac 1 -r 22000 "$d/$f.ogg"
done

Scour is an SVG optimizer/cleaner written in Python
https://github.com/scour-project/scour


"""
if sys.platform != "linux":

    def optimize(folder, filenames, **kw):
        for filename in filenames:
            yield filename

else:

    def optimize(folder, filenames, **kw):
        print("optimizing", folder)
        png_quality = 50

        done_list = []

        if os.popen("pngquant 2>&1").read().count("pngfile"):
            print(f"    -> with pngquant --quality {png_quality}", folder)
        else:
            png_quality = -1

        has_ffmpeg = os.popen("ffmpeg -version").read().count("version")

        truncate = len(str(folder))

        def translated(fn):
            nonlocal truncate
            return str(fn)[truncate:]

        # turn off all opt
        if "--no_opt" in sys.argv:
            for fp in filenames:
                if fp.stem.endswith("-pygbag"):
                    continue

                if fp.suffix == ".mp3":
                    continue

                if fp not in done_list:
                    done_list.append(fp)
                    yield fp.as_posix()
            return

        for fp in filenames:
            if fp.suffix == ".png":
                if png_quality >= 0:
                    if fp.stem.endswith("-pygbag"):
                        pass  # yield that file
                    else:
                        # .with_stem() 3.9+
                        opt = Path(f"{folder}/{fp.parent}/{fp.stem}-pygbag.png")

                        if opt.is_file():
                            # this is the no opt source, skip it
                            print("opt-skip(38)", fp)
                            continue

                        osexec = f'pngquant -f --ext -pygbag.png --quality {png_quality} "{folder}{fp}"'
                        os.system(osexec)
                        if opt.is_file():
                            yield translated(opt)
                            continue
                        else:
                            print("ERROR", osexec, "for", opt)

            elif fp.suffix in [".mp3", ".wav", ".ogg", ".flac"]:
                if fp.stem.endswith("-pygbag"):
                    pass  # yield that file
                else:
                    opt = Path(f"{folder}/{fp.parent}/{fp.stem}-pygbag.ogg")
                    if opt.is_file():
                        # this is the no opt source, skip it
                        print("opt-skip(73)", fp)
                        continue

                    osexec = f'ffmpeg -i "{folder}{fp}" -ac 1 -r 22000 "{opt}"'

                    if has_ffmpeg:
                        os.system(osexec)

                    if opt.is_file():
                        yield translated(opt)
                        continue
                    else:
                        if has_ffmpeg:
                            print("ERROR", osexec, "for", opt)

                        if fp.suffix == ".mp3":
                            print(
                                f"""

       ERROR: MP3 audio format is not allowed on web, convert {fp} to ogg

"""
                            )
                            sys.exit(3)

            if fp not in done_list:
                done_list.append(fp)
                yield fp.as_posix()
