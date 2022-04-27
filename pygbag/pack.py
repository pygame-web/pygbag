import sys, os
import zipfile
counter = 0
prelist = []

def archive(apkname):
    with zipfile.ZipFile(apkname, mode="x", compression=zipfile.ZIP_DEFLATED) as zf:

        def explore(pushpopd, newpath):
            global prelist, preloadedWasm, preloadedImages, preloadedAudios, counter

            import shutil

            if newpath.find("/.git")>=0:
                return

            for dirname, dirnames, filenames in os.walk(newpath):
                if dirname.find("/.git")>=0:
                    continue
                if dirname.find("/static/")>=0:
                    continue

                try:
                    os.chdir(dirname)
                    # print(f"\nNow in {os.getcwd()[LSRC:] or '.'}")

                except:
                    print("Invalid Folder :", pushpopd, newpath)

                for f in filenames:
                    if f.endswith('.gitignore'):
                        continue

                    if not os.path.isfile(f):
                        continue

                    ext = f.rsplit(".", 1)[-1].lower()

                    src = os.path.join(os.getcwd(), f)
                    src = f"assets{src[TRUNC:]}"
                    if not src in prelist:
                        zf.write(f, src)
                        print(src)
                        prelist.append(src)

                    counter += 1

                for subdir in dirnames:
                    if subdir != '.git':
                        explore(os.getcwd(), subdir)

            os.chdir(pushpopd)

        TRUNC=len(sys.argv[-1])

        explore(os.getcwd(), sys.argv[-1])

        print( counter )



