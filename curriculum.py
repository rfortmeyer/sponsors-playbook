"""60-lesson curriculum: foundations first, advanced structures last."""

COURSE_TITLE = "The Sponsor's Playbook"
COURSE_DESCRIPTION = (
    "A daily 15-minute lesson on the business principles an executive in a "
    "private-equity-backed company needs to know, from fund basics to advanced "
    "deal and capital structures."
)

MODULES = [
    ("How private equity works", "foundational", [
        "GPs, LPs, and the anatomy of a PE fund",
        "Fund economics: management fees, hurdle rates, carry, and the waterfall",
        "The fund lifecycle and why the clock drives every decision",
        "The three return levers: EBITDA growth, multiple expansion, and deleveraging",
        "IRR versus MOIC, and why sponsors watch both",
        "EBITDA, adjusted EBITDA, and the add-backs that get challenged",
        "Reading the three financial statements like a sponsor",
        "Free cash flow and working capital",
        "Enterprise value versus equity value",
        "Valuation multiples and comparable companies",
    ]),
    ("Operating inside a portfolio company", "foundational", [
        "The investment thesis and the 100-day plan",
        "Board governance in PE-backed companies",
        "The monthly reporting package, KPIs, and flash reports",
        "Budgeting and forecasting to sponsor and lender standards",
        "Management incentive plans: equity, options, vesting, and ratchets",
        "Working effectively with operating partners",
        "Cash conversion and working capital programs",
        "Pricing as a value creation lever",
        "Cost programs that protect the business",
        "Building the leadership team the thesis requires",
    ]),
    ("Deal mechanics", "intermediate", [
        "Anatomy of a leveraged buyout",
        "The back-of-the-envelope LBO",
        "The deal process: CIM, IOI, LOI, and exclusivity",
        "Quality of earnings and due diligence",
        "Purchase agreements: reps, warranties, indemnities, and R&W insurance",
        "Earnouts, rollover equity, and seller notes",
        "Working capital pegs and purchase price adjustments",
        "Management presentations: what buyers are really testing",
        "Add-on acquisitions and buy-and-build strategies",
        "Integration: making add-ons actually add value",
    ]),
    ("Capital structure and financing", "intermediate", [
        "The debt stack: senior, unitranche, second lien, and mezzanine",
        "Covenants: maintenance versus incurrence",
        "Leverage, coverage, and fixed charge ratios",
        "Reading a credit agreement as an operator",
        "Revolvers, liquidity, and the 13-week cash flow",
        "Preferred and structured equity",
        "Dividend recapitalizations",
        "Refinancing, repricing, and amend-and-extend",
        "Managing through a covenant breach",
        "The rise of private credit and what it changes",
    ]),
    ("Value creation and strategy", "advanced", [
        "What actually drives multiple expansion",
        "Quality of revenue: recurring, contracted, and transactional",
        "Customer concentration and how buyers discount it",
        "Unit economics and contribution margin",
        "Data, systems, and technology as value creation",
        "Platform strategy and programmatic M&A",
        "Organic growth playbooks sponsors trust",
        "The KPIs buyers pay a premium for",
        "Risk, compliance, and ESG as valuation factors",
        "Turnarounds and underperforming portfolio companies",
    ]),
    ("Exits and advanced structures", "advanced", [
        "Exit routes: strategic sale, secondary buyout, and IPO",
        "Preparing for exit eighteen to twenty-four months out",
        "Sell-side quality of earnings and vendor due diligence",
        "Continuation vehicles and GP-led secondaries",
        "Minority and growth equity structures",
        "Holdco and opco structures, and the tax considerations",
        "Rollover equity and the second bite of the apple",
        "Carve-outs and transition services agreements",
        "Restructuring: out-of-court deals, Chapter 11, and 363 sales",
        "Capstone: thinking like a sponsor",
    ]),
]

LESSONS = []
for mi, (module, level, titles) in enumerate(MODULES):
    for title in titles:
        LESSONS.append({
            "idx": len(LESSONS),
            "title": title,
            "module_num": mi + 1,
            "module": module,
            "level": level,
        })
TOTAL = len(LESSONS)
