import re
import os
import json
import traceback
import pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher
from datetime import datetime, timezone
from utils.error_store import error_store
from utils.week_file_save import current_week_file


# columns the cleaned notifications DataFrame must have
REQUIRED_COLUMNS = ["title", "clean_description", "link"]

# master directory: key column that identifies a master direction, plus the columns used for matching
MASTER_KEY = "id"
MASTER_REQUIRED_COLUMNS = [MASTER_KEY, "title", "text"]


def norm(s):
    cleaned = s.replace("–", "-").replace("—", "-")  # replace en-dashes with normal dashes
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ,-").lower()


def extract_names(text):
    DOC_TYPE = r"(?:Directions?|Guidelines?|Regulations?|Rules?|Circulars?|Framework|Scheme)"

    p1 = re.compile(
        r"Reserve Bank of India\s*[-–—]?\s*\(([^)]+)\)"
        r"(?:\s*\([^)]*\))*"
        r"\s*(?:[A-Za-z]+\s+){0,3}" + DOC_TYPE,
        re.IGNORECASE
    )

    p2 = re.compile(r"Reserve Bank of India\s*[-–—]\s*([A-Za-z ,]+?),?\s*Directions", re.IGNORECASE)

    if not isinstance(text, str):  # check if the input is string or not
        return []
    else:
        return [norm(x) for x in (p1.findall(text) + p2.findall(text))]


def get_lead(text):
    lead_break = re.compile(r"\n\s*2\.\s")  # extract text from the first para

    if not isinstance(text, str):
        return []

    else:
        m = lead_break.search(text)
        return text[:m.start()] if m else text[:600]  # first 600 characters if para 2 not found


def char_diff(a, b):
    diff = 0
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal":
            diff += max(i2 - i1, j2 - j1)
    return diff


def match_row(row, master_lookup):
    if row["discard_pre_match"]:
        return None, "discarded"
    for n in row["found_title"]:
        if n in master_lookup:
            return master_lookup[n], "title_match"
    for n in row["found_text"]:  # full text, not lead
        if n in master_lookup:
            return master_lookup[n], "text_match"
    return None, "no_match"


def bucket(row):
    if row["match_method"] == "discarded":
        return "discard"
    if row["match_method"] != "no_match":
        return "linked"
    if row["is_nbfc_relevant"]:
        has_citation = len(row["found_title"]) > 0 or len(row["found_text_lead"]) > 0
        return "nbfc_citation_unmatched" if has_citation else "nbfc_standalone"
    return "general"


def match_data(notifications_data):
    """
    notifications_data: cleaned DataFrame with at least the columns
    title, clean_description, link (as produced by clean_data).
    Returns True if new rows were matched and saved, otherwise False.
    """
    try:
        if not isinstance(notifications_data, pd.DataFrame) or notifications_data.empty:
            print("No notification data received")
            return False

        missing = [c for c in REQUIRED_COLUMNS if c not in notifications_data.columns]
        if missing:
            raise ValueError(f"notifications_data is missing columns: {missing}")

        file_path = os.path.dirname(os.path.realpath(__file__))
        in_dir_config_file = os.path.abspath(os.path.join(file_path, "..", "config.json"))

        in_dir_master_direction = os.path.abspath(
            os.path.join(file_path, "..", "data", "master_directory", "master_directory.jsonl"))
        master_dir = pd.read_json(in_dir_master_direction, lines=True)

        master_missing = [c for c in MASTER_REQUIRED_COLUMNS if c not in master_dir.columns]
        if master_missing:
            raise ValueError(f"master_directory.jsonl is missing columns: {master_missing}. "
                             f"Columns found: {list(master_dir.columns)}")

        out_path = os.path.join(file_path, "..", "data", "notifications_matched")
        os.makedirs(out_path, exist_ok=True)
        out_path_json = current_week_file(out_path, format="json")

        # work on a copy so the caller's DataFrame is not modified
        notifications = notifications_data.drop_duplicates(subset="link").copy()

        # skip links that were already matched and saved this week
        if os.path.exists(out_path_json) and os.path.getsize(out_path_json) > 0:
            done = set(pd.read_json(out_path_json, lines=True)["link"])
            notifications = notifications[~notifications["link"].isin(done)]

        if notifications.empty:
            print("Nothing new to match")
            return False

        notifications = notifications.reset_index(drop=True)

        notifications["found_title"] = notifications["title"].apply(extract_names)
        notifications["found_text"] = notifications["clean_description"].apply(extract_names)
        notifications["found_text_lead"] = [extract_names(get_lead(t)) for t in notifications["clean_description"]]

        master_dir["found_title"] = master_dir["title"].apply(extract_names)

        name_to_ids = defaultdict(set)
        for _, r in master_dir.iterrows():
            for name in r["found_title"]:
                name_to_ids[name].add(r[MASTER_KEY])

        master_lookup = {name: next(iter(ids)) for name, ids in name_to_ids.items() if len(ids) == 1}
        master_keys = list(master_lookup.keys())

        nbfc_pattern = re.compile(
            r"non[\s-]?banking financial compan|nbfc"
            r"|core investment compan(?:y|ies)"          # dropped bare \bcic\b - collides with Credit Information Company
            r"|standalone primary dealer|\bspd\b"
            r"|mortgage guarantee compan(?:y|ies)|\bmgc\b"
            r"|non-?operative financial holding compan(?:y|ies)|\bnofhc\b"
            r"|housing finance compan(?:y|ies)|\bhfc\b",
            re.IGNORECASE
        )

        other_entity_pattern = re.compile(
            r"regional rural bank"
            r"|urban co-?operative bank"
            r"|rural co-?operative bank"
            r"|state co-?operative bank"
            r"|district central co-?operative bank"
            r"|scheduled commercial bank"
            r"|commercial bank"
            r"|payments? bank"
            r"|small finance bank"
            r"|local area bank"
            r"|co-?operative bank"
            r"|banker and debt manager to government"
            r"|banker to governments? and banks"
            r"|consumer education and protection"
            r"|all india financial institutions?"
            r"|asset reconstruction compan(?:y|ies)"
            r"|credit information compan(?:y|ies)"
            r"|financial inclusion and development"
            r"|financial market"
            r"|issuer of currency"
            r"|payments? and settlement systems?",
            re.IGNORECASE
        )

        notifications["is_nbfc_in_title"] = notifications["title"].str.contains(nbfc_pattern, na=False)
        notifications["is_nbfc_relevant"] = (
            notifications["clean_description"].str.contains(nbfc_pattern, na=False) |
            notifications["is_nbfc_in_title"]
        )

        notifications["names_other_entity"] = notifications["title"].str.contains(other_entity_pattern, na=False)
        notifications["discard_pre_match"] = notifications["names_other_entity"] & ~notifications["is_nbfc_relevant"]

        notifications[["matched_id", "match_method"]] = list(
            notifications.apply(match_row, axis=1, args=(master_lookup,))
        )

        # fuzzy matching: closest master name within 5 characters
        fuzzy_candidates = []
        for idx, row in notifications[notifications["match_method"] == "no_match"].iterrows():
            for n in row["found_title"] + row["found_text_lead"]:
                scored = []
                for key in master_keys:
                    if abs(len(n) - len(key)) > 5:  # can't be within 5 edits, skip the slow check
                        continue
                    d = char_diff(n, key)
                    if d <= 5:
                        scored.append((d, key))
                if not scored:
                    continue
                best = min(d for d, _ in scored)
                for d, key in scored:
                    if d == best:  # keep ties so the ambiguity check sees them
                        fuzzy_candidates.append((idx, row["link"], n, key))

        fuzzy_df = pd.DataFrame(fuzzy_candidates, columns=["row_idx", "circular_id", "found_name", "closest_master_name"])
        print(f"{len(fuzzy_df)} candidates")

        fuzzy_df["master_id"] = fuzzy_df["closest_master_name"].map(master_lookup)
        dupe_check = fuzzy_df.groupby("row_idx")["master_id"].nunique()
        ambiguous_rows = dupe_check[dupe_check > 1].index

        safe_fuzzy = fuzzy_df[~fuzzy_df["row_idx"].isin(ambiguous_rows)].drop_duplicates("row_idx")
        for _, r in safe_fuzzy.iterrows():
            notifications.loc[r["row_idx"], "matched_id"] = master_lookup[r["closest_master_name"]]
            notifications.loc[r["row_idx"], "match_method"] = "fuzzy_match"

        # subject-code fallback for rows the name-based tiers missed
        ref_pattern = re.compile(r"([A-Z]+(?:\.[A-Z]+)+\.\d+)/([\d-]+)/(\d{4}-\d{2})")
        notifications["subject_code"] = notifications["clean_description"].str.extract(ref_pattern)[1]
        master_dir["subject_code"] = master_dir["text"].str.extract(ref_pattern)[1]

        code_counts = master_dir.dropna(subset=["subject_code"]).groupby("subject_code")[MASTER_KEY].nunique()
        generic = code_counts[code_counts > 1].index
        code_to_id = (master_dir[~master_dir["subject_code"].isin(generic)]
                        .dropna(subset=["subject_code"])
                        .drop_duplicates("subject_code")
                        .set_index("subject_code")[MASTER_KEY])

        found = notifications["subject_code"].map(code_to_id)
        hit = notifications["match_method"].eq("no_match") & found.notna()
        notifications.loc[hit, "matched_id"] = found[hit]
        notifications.loc[hit, "match_method"] = "subject_code_match"

        notifications["bucket"] = notifications.apply(bucket, axis=1)

        kept = notifications[notifications["bucket"] != "discard"].copy()

        if len(kept) > 0:
            payload = kept.to_json(orient="records", lines=True, force_ascii=False)
            if not payload.endswith("\n"):  # keeps appended runs on separate lines
                payload += "\n"
            with open(out_path_json, "a", encoding="utf-8") as f:
                f.write(payload)
            print(f"{len(kept)} : Candidates Saved")

            # re-read config right before writing so other steps' updates are not overwritten
            with open(in_dir_config_file) as config_file:
                config = json.load(config_file)
            config["data_check"]["matched_ref_file"] = str(out_path_json)
            with open(in_dir_config_file, "w") as config_file:
                json.dump(config, config_file, indent=4)
            return True

        else:
            print("None Saved")
            return False

    except Exception as e:
        error_store(str(e), traceback.format_exc(), str(datetime.now(timezone.utc)), "Not Applicable", "Match_data")
        return False


if __name__ == "__main__":
    # manual test: python match_data.py path/to/clean_notifications.csv
    import sys
    match_data(pd.read_csv(sys.argv[1]))