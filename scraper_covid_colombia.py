"""
Web scraper for COVID-19 data from Colombia's INS report.
Uses Amazon Nova Act to scan the full page and classify all data found into:
- general_data: overall country-level indicators
- time_data: evolution over time (graphs, tables, trends)
- regional_data: breakdown by department or region
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv
from nova_act import NovaAct

load_dotenv()

URL = "https://www.ins.gov.co/Noticias/Paginas/Coronavirus.aspx"
OUTPUT_FILE = "covid_colombia_data.json"


def scroll_and_load(nova: NovaAct):
    """Scroll through the full page to trigger lazy-loaded content and graphs."""
    print("  Loading full page content...")
    nova.act(
        "1. Wait for the page to fully load "
        "2. Slowly scroll from top to bottom of the entire page so all content, "
        "charts, graphs, maps, and tables become visible and rendered "
        "3. If you see any 'load more', 'show more', or expand buttons, click them "
        "4. Scroll back to the top when done"
    )


def extract_all_raw(nova: NovaAct) -> dict:
    """
    Scan the entire page and collect every piece of COVID-19 data visible,
    without assuming any section structure. Then classify into 3 buckets.
    """
    print("  Scanning entire page for all COVID-19 data...")

    # First pass: get everything visible as raw inventory
    raw = nova.act_get(
        "Read the entire page from top to bottom. "
        "List every single piece of data, number, statistic, label, chart title, "
        "graph value, map value, table row, date, or indicator you can find related to COVID-19. "
        "Do not skip anything. Do not assume sections exist. Just inventory everything you see.",
        schema={
            "type": "object",
            "properties": {
                "all_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                            "context": {"type": "string"}
                        }
                    }
                },
                "report_date_or_period": {"type": "string"},
                "page_title": {"type": "string"}
            }
        }
    )
    return raw.parsed_response or {}


def extract_interactive_graphs(nova: NovaAct) -> list:
    """Interact with every chart/graph/map to pull hidden data points."""
    print("  Interacting with charts and graphs...")

    nova.act(
        "1. Find every interactive chart, graph, or map on the page "
        "2. For each one: hover over data points to reveal tooltip values, "
        "click on bars or lines to expand data, interact with any filters or dropdowns "
        "3. For maps: hover over or click each visible department/region to reveal its data "
        "4. Note all values that appear during these interactions"
    )

    result = nova.act_get(
        "Based on your interactions with all charts, graphs, and maps on the page, "
        "extract every data point you revealed. For each chart or map include: "
        "what the chart shows, all data points with their labels and values, "
        "axis labels, legend entries, and any tooltip data you uncovered. "
        "For maps include every department or region value you found.",
        schema={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chart_or_map_title": {"type": "string"},
                    "type": {"type": "string"},
                    "data_points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"}
                            }
                        }
                    },
                    "axes": {"type": "string"},
                    "notes": {"type": "string"}
                }
            }
        }
    )
    return result.parsed_response or []


def classify_data(nova: NovaAct, raw_items: dict, graph_data: list) -> dict:
    """
    Ask Nova Act to classify all collected data into the 3 required buckets.
    This avoids assuming page structure — classification happens after full scan.
    """
    print("  Classifying collected data into general / time / regional buckets...")

    combined_context = json.dumps({
        "raw_page_data": raw_items,
        "interactive_graph_data": graph_data
    }, ensure_ascii=False)

    result = nova.act_get(
        f"Given the following COVID-19 data collected from the INS Colombia page, "
        f"classify every item into exactly one of three categories:\n"
        f"1. general_data: overall country-level indicators that are NOT broken down by time "
        f"or by region (e.g. total cases, total deaths, total recovered, positivity rate, "
        f"report date, etc.)\n"
        f"2. time_data: anything that shows how COVID-19 evolved over time "
        f"(daily/weekly/monthly series, trends, peaks, cumulative curves)\n"
        f"3. regional_data: anything broken down by department, city, or region of Colombia\n\n"
        f"Make sure every single data point from the input appears in one of the three sections. "
        f"Do not drop any data.\n\nData to classify:\n{combined_context}",
        schema={
            "type": "object",
            "properties": {
                "general_data": {
                    "type": "object",
                    "properties": {
                        "report_date": {"type": "string"},
                        "report_period": {"type": "string"},
                        "indicators": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "value": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "time_data": {
                    "type": "object",
                    "properties": {
                        "series": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "metric": {"type": "string"},
                                    "data_points": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "date": {"type": "string"},
                                                "value": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "peaks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "metric": {"type": "string"},
                                    "peak_value": {"type": "string"},
                                    "peak_date": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "regional_data": {
                    "type": "object",
                    "properties": {
                        "departments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "metrics": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "label": {"type": "string"},
                                                "value": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    )
    return result.parsed_response or {}


def main():
    api_key = os.getenv("NOVA_ACT_API_KEY")
    if not api_key:
        raise ValueError("NOVA_ACT_API_KEY not found in .env file")

    print(f"Starting COVID-19 data extraction from INS Colombia...")
    print(f"URL: {URL}\n")

    with NovaAct(
        starting_page=URL,
        headless=True,
        nova_act_api_key=api_key
    ) as nova:

        print("[1/4] Loading and rendering full page")
        scroll_and_load(nova)

        print("[2/4] Scanning all visible data")
        raw_items = extract_all_raw(nova)

        print("[3/4] Interacting with graphs and maps")
        graph_data = extract_interactive_graphs(nova)

        print("[4/4] Classifying data into sections")
        classified = classify_data(nova, raw_items, graph_data)

    output = {
        "metadata": {
            "source_url": URL,
            "scraped_at": datetime.now().isoformat(),
            "scraper": "Amazon Nova Act"
        },
        "general_data": classified.get("general_data", {}),
        "time_data": classified.get("time_data", {}),
        "regional_data": classified.get("regional_data", {})
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Data saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
