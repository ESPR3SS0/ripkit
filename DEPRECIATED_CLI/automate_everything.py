"""
This script is reponsible for using:
    - cargo_picky
    - go_picky 
    - binrip
"""



import numpy as np
from alive_progress import alive_it

from dataclasses import dataclass, asdict, fields

import magic


from enum import Enum
from pathlib import Path
import subprocess
from typing import Optional


#from cargo_picky import clone_crate, build_crate, Cargodb

from cargo_picky.cargo_picky import (
        clone_crate, get_registry_df, 
        get_target_productions, is_executable, get_file_type,
        Cargodb, build_crate, build_crate_many_target,
        RustcOptimization, RustcTarget, RustcStripFlags,
        #Compiler, ProgLang, FileType,
)

#from cargo_picky.cargo_builder import build_crate, build_crate_many_target

#from cargo_picky.cargo_reg_puller import (
#        clone_crate, get_registry_df, 
#        get_target_productions, is_executable, get_file_type,
#        Cargodb, Coptimization
#)

#from cargo_picky.cargo_types import RustcOptimization, RustcTarget, \
#                        RustcStripFlags
#
#from ripbin.analyzer.analyzer_types import Compiler, ProgLang, FileType, Coptimization


from ripbin.ripbin import (
    get_registry, AnalysisType, FileType, Compiler, ProgLang,
    generate_minimal_labeled_features, 
    generate_minimal_unlabeled_features, 
    save_and_register_analysis,
    )

#from ripbin.analyzer.analysis_save import is_db_formated, init_db, db_save_analysis, ___db_dumb_save_DONT_USE

#from ripbin.analyzer.binary_analyzer import objdump_cp, minimal_gen_data, generate_minimal_labeled_features

#from ripbin.analyzer.ripbin_db import save_and_register_analysis

#from go_picky.go_types import GoTarget, GoOptimization

from typing import Tuple

# Function to build crate and anaylis files in crate of 
# interest

def clone_build_analyze(crate: str, opt_lvl: RustcOptimization, 
                target: RustcTarget, strip: RustcStripFlags)->list:

    if crate not in list(get_registry_df().name):
        st = f"No crate of name {crate}"
        raise Exception(st)

    # Clone the crate
    clone_crate(crate)

    # Build the crate
    build_crate(crate,opt_lvl,target,strip)

    # Get files of interest from the crate at the target <target>
    files_of_interest = get_target_productions(crate, target)

    numpy_stacks = []
    for file in files_of_interest:
        # This is a known file, therefore to the model I 
        # this is training data 

        # This means the information for each byte is:
        # byte, addr, is_start, is_middle, is_end. 
        file_data = np.vstack(list(minimal_gen_data(file)))

        numpy_stacks.append((file,file_data))

    return numpy_stacks 


def get_labeled_stacks(crate:str, target: RustcTarget):
    # Get files of interest from the crate at the target <target>
    files_of_interest = get_target_productions(crate, target)

    numpy_stacks = []
    for file in files_of_interest:
        # This is a known file, therefore to the model I 
        # this is training data 

        # This means the information for each byte is:
        # byte, addr, is_start, is_middle, is_end. 
        file_data = np.vstack(list(minimal_gen_data(file)))

        numpy_stacks.append((file,file_data))

    return numpy_stacks 

def get_unlabeled_stacks(crate:str, target: RustcTarget):
    # Get files of interest from the crate at the target <target>
    files_of_interest = get_target_productions(crate, target)

    numpy_stacks = []
    for file in files_of_interest:
        # This is a known file, therefore to the model I 
        # this is training data 

        # This means the information for each byte is:
        # byte, addr, is_start, is_middle, is_end. 
        file_data = np.vstack(list(minimal_gen_data_testing(file)))

        numpy_stacks.append((file,file_data))

    return numpy_stacks 




def clone_build_analyze_for_testing(crate: str, opt_lvl: RustcOptimization, 
                target: RustcTarget, strip: RustcStripFlags)->list:


    if crate not in list(get_registry_df().name):
        st = f"No crate of name {crate}"
        raise Exception(st)

    # Clone the crate
    clone_crate(crate)

    # Build the crate
    build_crate(crate,opt_lvl,target,strip)

    # Get files of interest from the crate at the target <target>
    files_of_interest = get_target_productions(crate, target)

    numpy_stacks = []
    for file in files_of_interest:
        # This is a known file, therefore to the model I 
        # this is training data 

        # This means the information for each byte is:
        # byte, addr, is_start, is_middle, is_end. 
        file_data = np.vstack(list(minimal_gen_data_testing(file)))

        numpy_stacks.append((file,file_data))

    return numpy_stacks 

def clone_build_analyze_save_cargo(crate: str, 
                                   opt_lvl: RustcOptimization, 
                                   target: RustcTarget, 
                                   analysis_type: AnalysisType,
                                   strip = RustcStripFlags.NOSTRIP,
                                   ):
    """
        Clone the crate 
        Build the crate 
        Analyze a file of interest, must executable
        Save .npz file from analysis
    """

    # Clone the crate
    clone_crate(crate)

    # Build the crate
    build_crate(crate,opt_lvl,target,strip)

    # Get files of interest from the crate at the target <target>
    files_of_interest = [x for x in get_target_productions(crate, target) 
        if is_executable(x)]

    if len(files_of_interest) < 1:
        raise Exception("Error, no exectuables to analyze")

    bin_f = files_of_interest[0]


    if analysis_type == AnalysisType.DEC_REPR_BYTE_PLUS_FUNC_LABELS:
        # Get the numpy generator for the file analysis
        gen = generate_minimal_labeled_features(bin_f,use_one_hot=False)
    elif analysis_type == AnalysisType.ONEHOT_PLUS_FUNC_LABELS:
        # Get the numpy generator for the file analysis
        gen = generate_minimal_labeled_features(bin_f,use_one_hot=True)
    else:
        raise Exception("Unknown AnalysisType")


    # Register and save analysis
    save_and_register_analysis(bin_f,
                               gen,
                               analysis_type,
                               ProgLang.RUST,
                               Compiler.RUSTC,
                               FileType.ELF_X86_64,
                               opt_lvl,
                               )



    return

#def grab_go_executables():#->list[Tuple[GoTarget,list[Path]]]:
#    """
#        Grab go packages installed from go_picky
#    """
#    # The go packages are at 
#    #   ~/.go_picky/bin_install/<target>/bin/*
#    #       -or-
#    #   ~/.go_picky/bin_install/<target>/bin/<target>/*
#    
#    # I am going to check those two PATHS 
#    # @TODO: Hardcoded for now
#
#    base_dir = Path("~/.go_picky/bin_install/").expanduser().resolve()
#
#    if not base_dir.exists():
#        raise Exception("Base dir does not exist")
#
#    # Make a alist of valid targets
#    valid_targets = ["_".join(x.value) for x in GoTarget]
#
#    # Get the targets in the base dir
#    targets = [x.resolve() for x in base_dir.iterdir() 
#        if x.name in valid_targets]
#
#    ret_list = []
#
#    # for each target check the two potential dirs 
#    for target in targets:
#
#        # Get the corresponding go target from the directory 
#        # name 
#        go_target = get_GoTarget_from_str(target.name)
#
#        path1 = target / Path("bin") 
#        path2 = target / Path("bin") / Path(target.name) 
#
#        # Check the 'deeper' dir first to see if it exists
#        if path2.exists(): 
#            files = [x.resolve() for x in path2.iterdir()]
#        elif path1.exists():
#            files = [x.resolve() for x in path1.iterdir()]
#        else:
#            # @TODO: Maybe more proper to raise exception?
#            files = []
#
#        ret_list.append((go_target, files))
#
#    return ret_list



    

#def get_GoTarget_from_str(x:str)->GoTarget:
#    for member in GoTarget:
#        if "_".join(member.value) == x:
#            return member
#    raise ValueError("No GoTarget for str")

def analyze_save_go_pkg(bin_f:Path):
    """
        Analyze and save the analysis of a go pkg 
    """

    # Get the numpy generator for the file analysis
    gen = generate_minimal_labeled_features(bin_f)

    # Opt level here is assumed to be zero or rather 
    # @TODO: the default opt level for go

    # Determine file type
    f_type = get_file_type(bin_f)

    # Need to assert file is not stripped because 
    # sometimes windows PE files are autostripped
    if "not stripped" in (x:= magic.from_file(bin_f)):
        is_stripped = False
    elif "stripped" in x:
        is_stripped = True
    else:
        raise Exception("Unknown wether file is or is not sripped")

    # Save the analysis 
    db_save_analysis(bin_f, 
                     gen, 
                     ProgLang.GO,
                     Compiler.GO,
                     f_type,
                     opt_lvl = GoOptimization.DEFUALT,
                     is_stripped = is_stripped)
    return

def analyze_go_pacakges():
    """
        
        Analyze every go pkg in the .go_picky dirextory
    """

    # Grab all the go exes
    exes = grab_go_executables()

    # Analyze each binary
    # need...
    for _, exe_list in exes:
        # List of files for the go target
        for bin_f in exe_list:
            analyze_save_go_pkg(bin_f)
    return

def find_and_analyze_c_files(path:Path=
                             Path("~/.c_bins/2k_bins/testSuites/").expanduser()
                                                                  .resolve()):
    """
        Assuming c_files are in ~/.c_bins
    """
    # The 2k_bins/testSuites/... is what were interesting inm
    # 
    # The dir struture is 
    #   .../<[x86|x64]{compiler}>/<comp><pkg><[32|64]>_<optlvl>_fname
    files = [x for x in path.rglob('*') if x.is_file()]

    for bin_f in files:
        if "Spec" in str(bin_f.resolve()):
            print("Skippijg spec")
            continue
        # get its opt_lvl 

        try:
            comp,pkg_name,bit,opt,bin_name = bin_f.name.split("_")
        except Exception as e:
            print("Bad format name: {}".format(bin_f.name))

        if comp == "llvm":
            compiler = Compiler.CLANG
        elif comp == "icc":
            compiler = Compiler.ICC
        elif comp == "gcc":
            compiler = Compiler.GCC
        else:
            raise Exception("Unkown compiler {} {}".format(comp,bin_f.name))

        if opt== "O3":
            opt_lvl = Coptimization.O3
        elif opt== "O2":
            opt_lvl = Coptimization.O2
        elif opt== "O1":
            opt_lvl = Coptimization.O1
        elif opt== "O0":
            opt_lvl = Coptimization.O0
        else:
            raise Exception("Unkown opt lvl{}".format(opt))


        # Get the numpy generator for the file analysis
        gen = generate_minimal_labeled_features(bin_f)
    
        # Opt level here is assumed to be zero or rather 
        # @TODO: the default opt level for go
    
        # Determine file type
        f_type = get_file_type(bin_f)
    
        # Need to assert file is not stripped because 
        # sometimes windows PE files are autostripped
        if "not stripped" in (x:= magic.from_file(bin_f)):
            is_stripped = False
        elif "stripped" in x:
            is_stripped = True
        else:
            raise Exception("Unknown wether file is or is not sripped")
        print(f"analyzing file {bin_f}")
    
        try:
            # Save the analysis 
            db_save_analysis(bin_f, 
                             gen, 
                             ProgLang.C,
                             compiler,
                             f_type,
                             opt_lvl = opt_lvl,
                             is_stripped = is_stripped)
        except Exception as e:
            print("Save error : {}".format(e))

    return


if __name__ == "__main__":


    # Get the registry of available analyzed files
    reg = get_registry()

    #files = reg[reg['analysis_type'] == AnalysisType.ONEHOT_PLUS_FUNC_LABELS.value]
    #files = reg[reg['prog_lang'] == ProgLang.RUST.value]['binary_name']

    # Get the current crates cloned
    crates = [x.name for x in 
        Cargodb.CLONED_DIR.value.iterdir()]


    # Get the crates.io registry
    crates_io = get_registry_df()


    new_crate_l = crates_io[~crates_io["name"].isin(crates)]['name'].to_list()

    #new_crate_l = []
    #for file in files:
    #    for crate in crates:
    #        #print(f"File {file} crate {crate}")
    #        if crate.name in file or file in crate.name:
    #            #print(f"For file {file} found crate {crate}")
    #            new_crate_l.append(crate)


    opt_lvls = [RustcOptimization.O0,
                RustcOptimization.O1,
                RustcOptimization.O2,
                RustcOptimization.O3,
                RustcOptimization.OS,
                RustcOptimization.OZ,
               ]

    count = 0
    # Build and anylze all the crates for each opt level
    bar = alive_it(new_crate_l, title=f"{len(new_crate_l)}")

    # Iterate over bar 
    for crate in bar:
        if bar.current > 1000:
            exit(1)

        print(f"Cloning, building, analyzing crate {crate}")

        for opt in opt_lvls:
            # Build analyze save 
            try:
                clone_build_analyze_save_cargo(crate,
                                    opt, 
                                    RustcTarget.X86_64_UNKNOWN_LINUX_GNU,
                                    AnalysisType.ONEHOT_PLUS_FUNC_LABELS)
                clone_build_analyze_save_cargo(crate,
                                    opt, 
                                    RustcTarget.X86_64_UNKNOWN_LINUX_GNU,
                                    AnalysisType.DEC_REPR_BYTE_PLUS_FUNC_LABELS)
            except Exception as e:
                print("Error with crate {}: {}".format(crate,e))


    # clone build analyze all of the files I have now 
    # analyze them, and save them for each optimization level



 
    # Analyze all the binaries that cargo has 
    # all the binaries that go has, and 




    #custom_crate_list = [
    #        'bartib',
    #        'mdbook',
    #        ]

    #targets = [
    #        RustcTarget.X86_64_UNKNOWN_LINUX_GNU,
    #        RustcTarget.I686_UNKNOWN_LINUX_GNU,
    #        RustcTarget.X86_64_PC_WINDOWS_GNU,
    #        RustcTarget.I686_PC_WINDOWS_GNU,
    #        ]
    #for crate in custom_crate_list:
    #    for target in targets:
    #        try:
    #            # Clone build then analzye crates 
    #            clone_build_analyze_save_cargo(crate, 
    #                                           RustcOptimization.O0, 
    #                                           target, 
    #                                           RustcStripFlags.NOSTRIP)
    #        except Exception as e:
    #            print("Issue with pkg {} for target {}: {}".format(crate, 
                                                                   #target, 
                                                                   #e))


    #file_data = clone_build_analyze("exa", RustcOptimization.O1, 
    #                    RustcTarget.X86_64_UNKNOWN_LINUX_GNU, 
    #                    RustcStripFlags.SYM_TABLE)


    #clone_build_analyze_save_cargo("ripgrep", RustcOptimization.O0, 
    #                    RustcTarget.X86_64_UNKNOWN_LINUX_GNU, 
    #                    RustcStripFlags.NOSTRIP)





    #print(file_data)

    #for file in files:
    #    objdump_cp(file)

        #df = gen_knownByte_df_for_sql(file, Compiler.RUSTC, ProgLang.RUST, Optimization.O1, True, RustcTarget.X86_64_UNKNOWN_LINUX_GNU, compile_cmd = "temp")
        #print(df)



