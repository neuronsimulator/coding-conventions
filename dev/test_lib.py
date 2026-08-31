from pathlib import Path
import re
import stat
import sys
import tempfile

sys.path.append(str(Path(__file__).resolve().parent.parent))

import cpp.lib  # noqa: E402


def test_project_root_standalone():
    module = Path("/repo/hpc-coding-conventions")
    expected = module.resolve()
    assert (
        cpp.lib.project_root_from_git_info(
            module, None, Path("/repo/hpc-coding-conventions/cpp")
        )
        == expected
    )
    assert cpp.lib.project_root_from_git_info(module, None, Path("/tmp")) == expected


def test_project_root_submodule_primary_clone():
    module = Path("/home/user/nrn/external/coding-conventions")
    superproject = Path("/home/user/nrn")
    cwd = Path("/home/user/nrn")
    assert (
        cpp.lib.project_root_from_git_info(module, superproject, cwd)
        == superproject.resolve()
    )


def test_project_root_submodule_linked_worktree():
    # git-dir would be <primary>/.git/worktrees/<name>, whose parent is NOT
    # the worktree root. --show-superproject-working-tree is the worktree.
    module = Path("/home/user/neuron/msvc-port/external/coding-conventions")
    superproject = Path("/home/user/neuron/msvc-port")
    cwd = Path("/home/user/neuron/msvc-port")
    assert (
        cpp.lib.project_root_from_git_info(module, superproject, cwd)
        == superproject.resolve()
    )


def test_project_root_cwd_inside_module():
    module = Path("/home/user/nrn/external/coding-conventions")
    superproject = Path("/home/user/nrn")
    cwd = Path("/home/user/nrn/external/coding-conventions/cpp")
    assert (
        cpp.lib.project_root_from_git_info(module, superproject, cwd)
        == module.resolve()
    )


def test_source_dir_live_git():
    """
    Integration: source_dir() must be a real working tree, not
    ``.git/worktrees``.
    """
    cpp.lib.source_dir.cache_clear()
    root = cpp.lib.source_dir()
    cc_root = Path(cpp.lib.__file__).resolve().parent.parent
    cwd = Path.cwd().resolve()
    try:
        cwd.relative_to(cc_root)
        in_cc = True
    except ValueError:
        in_cc = False
    assert root.is_dir()
    # The broken heuristic returned ``<primary>/.git/worktrees``.
    assert root.name != "worktrees"
    if in_cc:
        assert root == cc_root
        assert (root / "bin" / "format").is_file()
    else:
        assert (root / ".bbp-project.yaml").is_file()
        assert (cc_root / "bin" / "format").is_file()


def test_clang_tidy_conf_merger():
    orig_checks = "foo-*,bar-pika,-bar-foo"
    test_func = cpp.lib.ClangTidy.merge_clang_tidy_checks

    assert test_func(orig_checks, None) == orig_checks
    assert test_func(orig_checks, "") == orig_checks
    assert test_func(orig_checks, "-bar-pika") == "foo-*,-bar-foo,-bar-pika"
    assert test_func(orig_checks, "bar-pika") == "foo-*,-bar-foo,bar-pika"
    assert test_func(orig_checks, "-bar-*") == "foo-*,-bar-*"
    assert test_func(orig_checks, "bar-*") == "foo-*,bar-*"
    assert test_func(orig_checks, "-bar-*") == "foo-*,-bar-*"
    assert test_func(orig_checks, "-bar-foo") == "foo-*,bar-pika,-bar-foo"
    assert test_func(orig_checks, "bar-foo") == "foo-*,bar-pika,bar-foo"

    assert test_func("bar-foo", "-bar-*") == "-bar-*"

    assert test_func("", "-bar-pika") == "-bar-pika"
    assert test_func("", "bar-foo") == "bar-foo"
    assert test_func(None, None) is None


def test_where():
    """Test cpp.lib.where function"""
    with tempfile.TemporaryDirectory() as bin_dir:
        expected_paths = set()
        for name in [
            "clang-format",
            "clang-format-13",
            "clang-format-14",
            "clang-format-mp-13",
            "clang-format-mp-14",
            "clang-format-diff.py",
            "clang-format-mp-diff.py",
            "clang-format-14-diff.py",
            "clang-format-diff",
            "clang-format-mp-diff",
            "clang-format-14-diff",
        ]:
            Path(bin_dir, name).touch()
        for name in ["clang-format", "clang-format-13", "clang-format-mp-13"]:
            executable = Path(bin_dir, name)
            executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
            expected_paths.add(str(executable))
        for name in [
            "clang-format-diff.py",
            "clang-format-mp-diff.py",
            "clang-format-14-diff.py",
            "clang-format-diff",
            "clang-format-mp-diff",
            "clang-format-14-diff",
        ]:
            executable = Path(bin_dir, name)
            executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
        TOOLS = cpp.lib.BBPProject.TOOLS_DESCRIPTION
        names_regex = TOOLS["ClangFormat"]["names_regex"]
        names_exclude_regex = TOOLS["ClangFormat"]["names_exclude_regex"]
        paths = set(
            cpp.lib.where(
                "clang-format",
                regex=re.compile(names_regex),
                exclude_regex=re.compile(names_exclude_regex),
                paths=[bin_dir],
            )
        )
        assert paths == expected_paths
