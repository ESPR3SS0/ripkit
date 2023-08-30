"""
Cross compiling rust is not as easy as the rust book makes it sounds...
1. After following rust book instrutios to
    - rustup toolchain install <x_chain>
    - rustup target add <x_target>
    You also need the correct linker installed for rustc!!

So all this really meant was I must use cargo for building, because 
after:
    - rustup target add <x_target> 
    you can:
    - cargo build --target <x_target>

This is fine, and only using rustc was not going to get me far anyways.

This files roadmap:
    [] automate cargo building 
        [] package_dir
        [] optimizations
        [] strip or not strip 
    [] automate cross compiling 
    [] automate extracting rlib files
        [] "ar x *.rlib file" ; Which may produce alot of files
"""

from enum import Enum
from pathlib import Path
import subprocess
from typing import Optional
from .cargo_types import RustcTarget, CargoVariables, RustcStripFlags,\
                        RustcOptimization, Cargodb
REG_DIR = Cargodb.REG_DIR.value
CLONED_DIR = Cargodb.CLONED_DIR.value
EXTRACTED_TAR_DIR = Cargodb.EXTRACTED_TAR_DIR.value
DATA_DIR = Cargodb.DATA_DIR.value


def gen_cross_build_cmd(proj_path: Path, target: RustcTarget, 
                        strip_cmd: Optional[RustcStripFlags] = None, 
                        opt_lvl: Optional[RustcOptimization] = None):

    # First build the environment variables,
    # the CARGO_ENCODED_RUSTC_FLAGS -otherwise called- 
    #   CargoVariables.RUSTC_FLAGS 
    # Is being used to strip or not strip
    # 
    # And CARGO_PROFILE_DEV_OPT_LEVEL -otherwise called-
    #   CargoVariables.DEV_PROF_SET_OPT_LEVEL 
    # Is being used to set the optimizaition level
    substrs = []
    if strip_cmd is not None:
        substrs.append(f"{CargoVariables.RUSTC_FLAGS.value}='{strip_cmd.value}'")
    if opt_lvl is not None:
        substrs.append(f" {CargoVariables.DEV_PROF_SET_OPT_LEVEL.value}={opt_lvl.value}")

    substrs.append(f"cd {proj_path} && cross build --target={target.value}")
    #substrs.append(f"cd {proj_path} && cross build --manifest-path={proj_path.resolve()}/Cargo.toml --target={target.value}")

    full_build_str = " ".join(x for x in substrs)
    return full_build_str


def build_crate(crate: str, 
                opt_lvl: RustcOptimization = RustcOptimization.O1,
                target: RustcTarget = RustcTarget.X86_64_UNKNOWN_LINUX_GNU, 
                strip: RustcStripFlags = RustcStripFlags.NOSTRIP)->None:
    ''' Build the repo '''

    crate_path = CLONED_DIR.joinpath(crate)

    cmd = gen_cross_build_cmd(crate_path,target,strip, opt_lvl)
    #cmd = f"cd {CLONED_DIR} && " + cmd

    # If the crate doesn't exist dont run
    if not crate_path.exists(): 
        raise Exception(f"Crate {crate} has not been cloned")
    try: 
        output = subprocess.check_output(cmd, shell=True)
    except Exception as e:
        print(f"Error: {e} Failed to rustc compile command.")
        return
    return


def build_crate_many_target(crate: str, 
                opt_lvl: RustcOptimization, 
                targets: list[RustcTarget], 
                strip: RustcStripFlags,
                            stop_on_fail = False):
    ''' Build the repo '''

    # Log of failed builds
    failed_builds = []
    built_targets = []


    for target in targets:
        try:
            build_crate(crate,opt_lvl, target, strip)
            built_targets.append((crate,opt_lvl,target,strip))
        except Exception as e:
            if stop_on_fail: raise e
            failed_builds.append((crate,opt_lvl,target,strip))
    return (built_targets, failed_builds)



if __name__ == "__main__":

    #bul_str = gen_cross_build_cmd(Path("hello.rs"), 
    #            target = RustcTarget.X86_64_PC_WINDOWS_GNU, 
    #            strip_cmd = RustcStripFlags.SYM_TABLE, 
    #            opt_lvl = RustcOptimization.O1)
    build_crate('exa',RustcOptimization.O0, RustcTarget.X86_64_PC_WINDOWS_MSVC, RustcStripFlags.NOSTRIP)
    print("done")
