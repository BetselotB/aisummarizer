"""Detail tier configuration for study guide depth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DETAIL_TIERS = ("concise", "standard", "detailed", "comprehensive")
DEFAULT_DETAIL_TIER = "standard"


@dataclass(frozen=True)
class TierConfig:
    id: str
    label: str
    description: str
    use_master_plan: bool
    split_chapters: bool
    chapter_min: int
    chapter_max: int
    min_blocks: int
    max_blocks: int
    min_blocks_per_section: int
    excerpt_chars: int
    exam_traps_min: int
    exam_traps_max: int
    outline_temp: float
    chapter_temp: float
    subtitle_suffix: str


TIER_CONFIGS: dict[str, TierConfig] = {
    "concise": TierConfig(
        id="concise",
        label="Concise",
        description="Quick review — essential facts and definitions only",
        use_master_plan=False,
        split_chapters=False,
        chapter_min=2,
        chapter_max=4,
        min_blocks=4,
        max_blocks=8,
        min_blocks_per_section=3,
        excerpt_chars=25_000,
        exam_traps_min=5,
        exam_traps_max=8,
        outline_temp=0.25,
        chapter_temp=0.3,
        subtitle_suffix="Concise Review",
    ),
    "standard": TierConfig(
        id="standard",
        label="Standard",
        description="Balanced exam notes with tables, examples, and key takeaways",
        use_master_plan=False,
        split_chapters=False,
        chapter_min=3,
        chapter_max=8,
        min_blocks=6,
        max_blocks=15,
        min_blocks_per_section=5,
        excerpt_chars=40_000,
        exam_traps_min=8,
        exam_traps_max=15,
        outline_temp=0.3,
        chapter_temp=0.35,
        subtitle_suffix="Study Guide",
    ),
    "detailed": TierConfig(
        id="detailed",
        label="Detailed",
        description="In-depth coverage with expanded sections and richer reference tables",
        use_master_plan=True,
        split_chapters=False,
        chapter_min=4,
        chapter_max=8,
        min_blocks=10,
        max_blocks=20,
        min_blocks_per_section=8,
        excerpt_chars=50_000,
        exam_traps_min=10,
        exam_traps_max=18,
        outline_temp=0.3,
        chapter_temp=0.4,
        subtitle_suffix="Detailed Study Notes",
    ),
    "comprehensive": TierConfig(
        id="comprehensive",
        label="Comprehensive",
        description="Full exam-ready breakdown — AI plans every section, then writes deep structured notes",
        use_master_plan=True,
        split_chapters=True,
        chapter_min=5,
        chapter_max=12,
        min_blocks=15,
        max_blocks=35,
        min_blocks_per_section=6,
        excerpt_chars=65_000,
        exam_traps_min=12,
        exam_traps_max=22,
        outline_temp=0.25,
        chapter_temp=0.4,
        subtitle_suffix="Comprehensive Exam Notes",
    ),
}


def normalize_detail_tier(tier: str | None) -> str:
    t = (tier or DEFAULT_DETAIL_TIER).strip().lower()
    return t if t in TIER_CONFIGS else DEFAULT_DETAIL_TIER


def get_tier_config(tier: str | None) -> TierConfig:
    return TIER_CONFIGS[normalize_detail_tier(tier)]


def tier_options_for_api() -> list[dict[str, str]]:
    return [
        {
            "id": cfg.id,
            "label": cfg.label,
            "description": cfg.description,
        }
        for cfg in TIER_CONFIGS.values()
    ]


def outline_tier_addon(cfg: TierConfig) -> str:
    return (
        f"\n\nDETAIL TIER: {cfg.label.upper()} ({cfg.id})\n"
        f"- Create {cfg.chapter_min}–{cfg.chapter_max} chapters based on source length\n"
        f"- Each chapter should plan for {cfg.min_blocks}–{cfg.max_blocks} content blocks when written\n"
        f"- Subtitle should end with or include: {cfg.subtitle_suffix}\n"
    )


def chapter_tier_addon(cfg: TierConfig, priority: str) -> str:
    high = priority == "high"
    min_b = cfg.min_blocks + (4 if high else 0)
    max_b = cfg.max_blocks + (6 if high else 0)
    return (
        f"\n\nDETAIL TIER: {cfg.label.upper()}\n"
        f"- Produce {min_b}–{max_b} blocks for this chapter\n"
        f"- {'Exam-critical chapter — maximum depth, multiple tables and examples' if high else 'Cover all concepts thoroughly'}\n"
    )


def appendix_tier_addon(cfg: TierConfig) -> str:
    return (
        f"\n\nDETAIL TIER: {cfg.label.upper()}\n"
        f"- Include {cfg.exam_traps_min}–{cfg.exam_traps_max} exam_traps\n"
        f"- Cheat sheet density: {'dense reference tables' if cfg.id != 'concise' else 'compact quick-reference only'}\n"
    )


def master_plan_tier_addon(cfg: TierConfig, extra_context: str) -> str:
    sections = "4–8 detailed sections each with objectives, key concepts, and must-cover items" if cfg.split_chapters else "3–6 sections per chapter"
    lines = [
        f"\n\nDETAIL TIER: {cfg.label.upper()} — produce a MASTER PLAN for exam-ready notes",
        f"- Plan {cfg.chapter_min}–{cfg.chapter_max} chapters",
        f"- Each chapter needs {sections}",
        f"- Subtitle: include '{cfg.subtitle_suffix}'",
    ]
    if extra_context.strip():
        lines.append(f"- USER CONTEXT (honor this): {extra_context.strip()}")
    return "\n".join(lines) + "\n"


def section_tier_addon(cfg: TierConfig) -> str:
    return (
        f"\n\nDETAIL TIER: {cfg.label.upper()} — write ONE section of a comprehensive chapter\n"
        f"- Minimum {cfg.min_blocks_per_section} content blocks\n"
        f"- Deep explanations, definitions, examples, and at least one table or note box\n"
    )
