import io

from opensteps.approval import prompt_for_approval


def test_yes_approves():
    out = io.StringIO()
    approved = prompt_for_approval("pay $100 to Acme", io.StringIO("y\n"), out)
    assert approved
    assert "pay $100 to Acme" in out.getvalue()


def test_no_rejects():
    approved = prompt_for_approval("x", io.StringIO("n\n"), io.StringIO())
    assert not approved


def test_empty_input_rejects():
    approved = prompt_for_approval("x", io.StringIO(""), io.StringIO())
    assert not approved


def test_garbage_rejects():
    approved = prompt_for_approval("x", io.StringIO("sure why not\n"), io.StringIO())
    assert not approved


def test_timeout_rejects():
    import os

    read_fd, write_fd = os.pipe()  # never written -> must time out
    try:
        with os.fdopen(read_fd, "r") as silent:
            approved = prompt_for_approval("x", silent, io.StringIO(), timeout=0.2)
        assert not approved
    finally:
        os.close(write_fd)
