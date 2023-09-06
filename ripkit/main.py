import typer
import pandas as pd
from typing_extensions import Annotated
from alive_progress import alive_bar, alive_it
from pathlib import Path


app = typer.Typer()

from ripkit.cargo_picky import (
    get_target_productions,
    is_executable,
    init_crates_io,
    crates_io_df,
    clone_crate,
    is_remote_crate_exe,
    LocalCratesIO,
    build_crate,
    RustcStripFlags,
    RustcOptimization,
    RustcTarget
)

from ripkit.ripbin import (
    save_analysis,
    calculate_md5,
    RustFileBundle,
    generate_minimal_labeled_features,
    generate_minimal_unlabeled_features,
    POLARS_generate_minimal_unlabeled_features,
    get_registry,
    save_and_register_analysis,
    AnalysisType,
    FileType,
    Compiler,
    ProgLang,
    RustcOptimization,
)

@app.command()
def init():
    '''
    Initialize ripkit with rust data base,
    and register files
    '''
    init_crates_io()
    return

@app.command()
def is_crate_exe(
        crate: Annotated[str, typer.Argument()]):

    print(is_remote_crate_exe(crate))
    return


@app.command()
def cargo_clone(
        crate: Annotated[str, typer.Argument()]):

    clone_crate(crate)

    return

@app.command()
def show_cratesio(
    column: 
        Annotated[str, typer.Option()] = '',
    ):
    '''
    Show the head of cratesw io dataframe
    '''

    # Get the df
    crates_df = crates_io_df()


    if column == '':
        print(crates_df.head())
    else:
        print(crates_df[column])
    print(crates_df.columns)


@app.command()
def clone_many_exe(
    number: 
        Annotated[int,typer.Argument()]):
    '''
    Clone many exes
    '''

    # Get the remote crate reg
    reg = crates_io_df()

    # List of crate current installed
    installed_crates = [x.name for x in Path(LocalCratesIO.CRATES_DIR.value).iterdir() if x.is_dir()
    ]

    # List of crate names
    crate_names = [x for x in reg['name'].tolist() if x not in installed_crates]

    cloned_count = 0
    with alive_bar(number) as bar:
        for i, crate in enumerate(crate_names):

            if i % 1000 == 0:
                print(f"Searching... {i} crates so far")
            # See if the crate is exe before cloning
            if is_remote_crate_exe(crate):
                try:
                    clone_crate(crate)
                    cloned_count+=1
                    bar()
                except Exception:
                    continue

            else:
                bar(skipped=True)

            # Break out of the loop if enough have cloned
            if cloned_count >= number:
                break


@app.command()
def build(
    crate: Annotated[str, typer.Argument(help="crate name")],
    opt_lvl: Annotated[str, typer.Argument(help="O0, O1, O2, O3, Oz, Os")],
    bit: Annotated[str, typer.Argument(help="32 or 64")],
    filetype: Annotated[str, typer.Argument(help="pe or elf")],
    strip: Annotated[bool, typer.Option()] = False,
    ):
    '''
    Build a crate for a specific target
    '''

    #TODO: For simpilicity I prompt for only
    # 64 vs 32 bit and pe vs elf. Really I 
    # should prompt for the whole target arch
    # b/c theres many different ways to get
    # a 64bit pe  or 32bit elf 

    if opt_lvl == "O0":
        opt = RustcOptimization.O0
    elif opt_lvl == "O1":
        opt = RustcOptimization.O0
    elif opt_lvl == "O2":
        opt = RustcOptimization.O0
    elif opt_lvl == "O3":
        opt = RustcOptimization.O0
    elif opt_lvl == "Oz":
        opt = RustcOptimization.OZ
    elif opt_lvl == "Os":
        opt = RustcOptimization.OS
    else:
        print("UNknown opt")
        return

    if bit == "64":
        if filetype == "elf":
            target = RustcTarget.X86_64_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.X86_64_PC_WINDOWS_GNU 
        else:
            print("UNknown filetype")
            return
    elif bit == "32":
        if filetype == "elf":
            target = RustcTarget.I686_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.I686_PC_WINDOWS_GNU 
        else:
            print("UNknown filetype")
            return
    else:
        print("UNknown bit")
        return

    if not strip:
        strip_lvl = RustcStripFlags.NOSTRIP
    else:
        # SYM_TABLE is the all the symbols
        strip_lvl = RustcStripFlags.SYM_TABLE


    build_crate(crate, opt, target, strip_lvl)

    print(f"Crate {crate} built")
    return


@app.command()
def build_all(
    opt_lvl: Annotated[str, typer.Argument(help="O0, O1, O2, O3, Oz, Os")],
    bit: Annotated[str, typer.Argument(help="32 or 64")],
    filetype: Annotated[str, typer.Argument(help="pe or elf")],
    strip: Annotated[bool, typer.Option()] = False,
    ):
    '''
    Build all the installed crates
    '''

    #TODO: For simpilicity I prompt for only
    # 64 vs 32 bit and pe vs elf. Really I 
    # should prompt for the whole target arch
    # b/c theres many different ways to get
    # a 64bit pe  or 32bit elf 

    if opt_lvl == "O0":
        opt = RustcOptimization.O0
    elif opt_lvl == "O1":
        opt = RustcOptimization.O1
    elif opt_lvl == "O2":
        opt = RustcOptimization.O2
    elif opt_lvl == "O3":
        opt = RustcOptimization.O3
    elif opt_lvl == "Oz":
        opt = RustcOptimization.OZ
    elif opt_lvl == "Os":
        opt = RustcOptimization.OS
    else:
        return

    if bit == "64":
        if filetype == "elf":
            target = RustcTarget.X86_64_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.X86_64_PC_WINDOWS_GNU 
        else:
            return
    elif bit == "32":
        if filetype == "elf":
            target = RustcTarget.I686_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.I686_PC_WINDOWS_GNU 
        else:
            return
    else:
        return

    if not strip:
        strip_lvl = RustcStripFlags.NOSTRIP
    else:
        # SYM_TABLE is the all the symbols
        strip_lvl = RustcStripFlags.SYM_TABLE








    # List of crate current installed
    installed_crates = [x.name for x in Path(LocalCratesIO.CRATES_DIR.value).iterdir() if x.is_dir()
    ]

    for crate in alive_it(installed_crates):
        build_crate(crate, opt, target, strip_lvl)



@app.command()
def list_cloned():
    '''
    List the cloned crates
    '''

    # List of crate current installed
    installed_crates = [x.name for x in Path(LocalCratesIO.CRATES_DIR.value).iterdir() if x.is_dir()]

    for crate in installed_crates:
        print(crate)
                        


@app.command()
def analyze(bin_path: Annotated[str, typer.Argument()],
            language: Annotated[str, typer.Argument()],
            opt_lvl: Annotated[str, typer.Argument(help="O0, O1, O2, O3, Oz, Os")],
            bit: Annotated[str, typer.Argument(help="32 or 64")],
            filetype: Annotated[str, typer.Argument(help="pe or elf")],
            save: Annotated[bool, typer.Option()] = True,
            ):
    '''
    Analyze binary file 
    '''

    binary = Path(bin_path).resolve()
    if not binary.exists():
        print(f"Binary {binary} doesn't exist")
        return

    # Generate analysis
    print("Generating Tensors...")
    data = generate_minimal_labeled_features(binary)
    print("Tensors generated")


    # Create the file info
    print("Calculating bin hash...")
    binHash = calculate_md5(binary)
    print("bin hash calculated...")

    # Create the file info
    info = RustFileBundle(binary.name,
                          binHash,
                          "",
                          filetype,
                          opt_lvl,
                          binary.name,
                          "",
                          "")

    print("Saving Tensor and binary")
    # Save analyiss
    save_analysis(binary,
                    data,
                    AnalysisType.ONEHOT_PLUS_FUNC_LABELS,
                    info)
    print("Done!")


#@app.command()
#def add_binary(
#    binary: Annotated[str, typer.Argument(help="Abs path to binary")],
#    ):
#    return

@app.command()
def build_analyze_all(
    opt_lvl: Annotated[str, typer.Argument()],
    bit: Annotated[int, typer.Argument()],
    filetype: Annotated[str, typer.Argument()],
    ):
    '''
    Build and analyze pkgs
    '''
    if opt_lvl == "O0":
        opt = RustcOptimization.O0
    elif opt_lvl == "O1":
        opt = RustcOptimization.O1
    elif opt_lvl == "O2":
        opt = RustcOptimization.O2
    elif opt_lvl == "O3":
        opt = RustcOptimization.O3
    elif opt_lvl == "Oz":
        opt = RustcOptimization.OZ
    elif opt_lvl == "Os":
        opt = RustcOptimization.OS
    else:
        print("Invalid opt lvl")
        return

    if bit == 64:
        if filetype == "elf":
            target = RustcTarget.X86_64_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.X86_64_PC_WINDOWS_GNU 
        else:
            print("Invlaid filetype")
            return
    elif bit == 32:
        if filetype == "elf":
            target = RustcTarget.I686_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.I686_PC_WINDOWS_GNU 
        else:
            print("Invlaid filetype")
            return
    else:
        print(f"Invlaid bit lvl {bit}")
        return

    # List of crate current installed
    installed_crates = [x.name for x in Path(LocalCratesIO.CRATES_DIR.value).iterdir() if x.is_dir()
    ]


    # Build the crate, add the binary to a list of binaries
    bins = []
    for crate in alive_it(installed_crates):
        build_crate(crate, opt, target, RustcStripFlags.NOSTRIP)

        # Get files of interest from the crate at the target <target>
        files_of_interest = [x for x in get_target_productions(crate, target) if is_executable(x)]

        if files_of_interest != []:
            bins.append(files_of_interest[0])


    for binary in alive_it(bins):

        try:

            # Analyze the file
            analyze(binary,
                    'rust',
                    opt.value,
                    str(bit),
                    str(filetype),
                    )

        except Exception:
            print(f"Error for file {binary}")
            pass






if __name__ == "__main__":
    app()
