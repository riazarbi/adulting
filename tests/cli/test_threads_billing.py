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


BASE = ("--kind", "project", "--category", "professional")


def test_currency_is_upper_cased(vault):
    r = new(vault, *BASE, "--name", "Acme Corp", "--currency", "zar", input="")
    assert r.returncode == 0, r.stderr
    assert fm(vault, "Projects", "Acme Corp")["currency"] == "ZAR"


def test_currency_without_rate_writes_no_rate(vault):
    """The old interactive path wrote `rate: 2500` when the rate prompt was
    left blank. With flags only, no rate is written and `hours` falls back
    to the vault config and then 2500 (see test_new_thread_is_immediately_loggable)."""
    new(vault, *BASE, "--name", "Acme Corp", "--currency", "zar", input="")
    assert "rate" not in fm(vault, "Projects", "Acme Corp")


def test_no_currency_omits_billing_fields(vault):
    r = new(vault, "--kind", "topic", "--category", "personal",
            "--name", "Woodworking", input="")
    assert r.returncode == 0, r.stderr
    text = vault.read("threads/Topics/Woodworking.md")
    assert "currency:" not in text
    assert "rate:" not in text


def test_explicit_rate_is_kept(vault):
    new(vault, *BASE, "--name", "Acme Corp", "--currency", "gbp", "--rate", "900", input="")
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
    new(vault, *BASE, "--name", "Acme Corp", "--currency", "zar", input="")
    r = vault.run("log", "Acme Corp", "kickoff", cli="hours")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2500 ZAR" in r.stdout


def test_generated_thread_passes_lint(vault):
    new(vault, *BASE, "--name", "Acme Corp", "--currency", "zar", "--rate", "900", input="")
    p = vault.home / "threads" / "Projects" / "Acme Corp.md"
    assert vault.run(str(p), cli="lint").returncode == 0
