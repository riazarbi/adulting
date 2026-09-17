"""`threads new` collects the billing defaults `hours` needs."""


def new(vault, *argv, **kw):
    return vault.run("new", *argv, cli="threads", **kw)


def fm(vault, kind, name):
    text = vault.read(f"threads/{kind}/{name}.md")
    body = text.split("---")[1]
    return dict(
        line.split(":", 1)[0].strip() and
        (line.split(":", 1)[0].strip(), line.split(":", 1)[1].strip())
        for line in body.strip().split("\n") if ":" in line
    )


def test_interactive_collects_currency_and_rate(vault):
    r = new(vault, input="1\n1\nAcme Corp\nzar\n\n")
    assert r.returncode == 0, r.stderr
    f = fm(vault, "Projects", "Acme Corp")
    assert f["currency"] == "ZAR"          # upper-cased
    assert f["rate"] == "2500"             # blank accepts the default


def test_blank_currency_omits_billing_fields(vault):
    r = new(vault, input="3\n2\nWoodworking\n\n")
    assert r.returncode == 0, r.stderr
    text = vault.read("threads/Topics/Woodworking.md")
    assert "currency:" not in text
    assert "rate:" not in text


def test_explicit_rate_is_kept(vault):
    new(vault, input="1\n1\nAcme Corp\ngbp\n900\n")
    assert fm(vault, "Projects", "Acme Corp")["rate"] == "900"


def test_flags_skip_prompts_entirely(vault):
    r = new(vault, "--kind", "project", "--category", "professional",
            "--name", "Flags Only", "--currency", "GBP", "--rate", "900",
            input="")
    assert r.returncode == 0, r.stderr
    f = fm(vault, "Projects", "Flags Only")
    assert f["currency"] == "GBP" and f["rate"] == "900"


def test_flags_without_billing_stay_unbilled(vault):
    r = new(vault, "--kind", "topic", "--category", "personal",
            "--name", "Reading", input="")
    assert r.returncode == 0, r.stderr
    assert "currency:" not in vault.read("threads/Topics/Reading.md")


def test_bad_currency_rejected(vault):
    r = new(vault, "--kind", "project", "--category", "professional",
            "--name", "Bad", "--currency", "rands", input="")
    assert r.returncode != 0
    assert not (vault.home / "threads" / "Projects" / "Bad.md").exists()


def test_rate_without_currency_rejected(vault):
    r = new(vault, "--kind", "project", "--category", "professional",
            "--name", "Bad", "--rate", "900", input="")
    assert r.returncode != 0


def test_new_thread_is_immediately_loggable(vault):
    """The gap this closes: a fresh billable thread should not need a
    hand-edit before `hours log` works."""
    new(vault, input="1\n1\nAcme Corp\nzar\n\n")
    r = vault.run("log", "Acme Corp", "kickoff", cli="hours")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2500 ZAR" in r.stdout


def test_generated_thread_passes_lint(vault):
    new(vault, input="1\n1\nAcme Corp\nzar\n\n")
    p = vault.home / "threads" / "Projects" / "Acme Corp.md"
    assert vault.run(str(p), cli="lint").returncode == 0
