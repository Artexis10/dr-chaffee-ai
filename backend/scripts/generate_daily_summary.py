#!/usr/bin/env python3
"""
Generate Daily Summary CLI

Generates an LLM-powered daily usage digest for a specific date.
Can be run manually or via cron/scheduled task.

Usage:
    # Generate for yesterday (default)
    python -m scripts.generate_daily_summary

    # Generate for a specific date
    python -m scripts.generate_daily_summary --date 2025-12-02

    # Force regenerate even if summary exists
    python -m scripts.generate_daily_summary --date 2025-12-02 --force

Environment:
    DATABASE_URL: PostgreSQL connection string
    OPENAI_API_KEY: OpenAI API key for summary generation
"""

import os
import sys
import argparse
import logging
from datetime import date, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Generate daily usage summary for Dr. Chaffee AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate for yesterday
    python -m scripts.generate_daily_summary

    # Generate for specific date
    python -m scripts.generate_daily_summary --date 2025-12-02

    # Force regenerate
    python -m scripts.generate_daily_summary --force
        """
    )

    parser.add_argument(
        '--date', '-d',
        type=str,
        default=None,
        help='Date to generate summary for (YYYY-MM-DD). Defaults to yesterday.'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force regenerate even if summary already exists.'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without generating summary.'
    )

    args = parser.parse_args()

    # Validate environment
    if not os.getenv('DATABASE_URL'):
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    if not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # Parse date
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = date.today() - timedelta(days=1)

    # Validate date is not in future
    if target_date > date.today():
        logger.error(f"Cannot generate summary for future date: {target_date}")
        sys.exit(1)

    logger.info(f"Generating daily summary for {target_date}")

    if args.dry_run:
        logger.info("[DRY RUN] Would generate summary - exiting")
        return

    # Import and run generation
    try:
        from api.daily_summaries import generate_daily_summary, aggregate_daily_stats

        # First show stats
        stats = aggregate_daily_stats(target_date)
        logger.info(f"Stats for {target_date}:")
        logger.info(f"  - Total queries: {stats.total_queries}")
        logger.info(f"  - Answers: {stats.total_answers}")
        logger.info(f"  - Searches: {stats.total_searches}")
        logger.info(f"  - Distinct sessions: {stats.distinct_sessions}")
        logger.info(f"  - Success rate: {stats.success_rate * 100:.1f}%")

        if stats.total_queries == 0:
            logger.warning(f"No queries found for {target_date}. Summary will note quiet day.")

        # Generate summary
        result = generate_daily_summary(
            summary_date=target_date,
            force_regenerate=args.force,
        )

        logger.info("Summary generated successfully!")
        logger.info(f"  - ID: {result['id']}")
        logger.info(f"  - Created: {result['created_at']}")

        # Print summary preview
        summary_text = result['summary_text']
        preview = summary_text[:500] + "..." if len(summary_text) > 500 else summary_text
        logger.info(f"\n--- Summary Preview ---\n{preview}\n--- End Preview ---")

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Done!")


if __name__ == '__main__':
    main()
