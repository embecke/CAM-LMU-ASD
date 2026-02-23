from __future__ import annotations

import math

import pandas as pd


def _window_stats(minutes: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> tuple[int, int, float]:
	"""Return observed minutes, expected minutes, and coverage for [start, end)."""
	if pd.isna(start) or pd.isna(end) or end <= start:
		return 0, 0, 0.0

	window_minutes = minutes[(minutes >= start) & (minutes < end)]
	observed = int(window_minutes.nunique())
	expected = int(math.ceil((end - start).total_seconds() / 60))
	if expected <= 0:
		return observed, expected, 0.0
	return observed, expected, float(observed) / float(expected)


def _sleep_windows(df_sleep: pd.DataFrame) -> pd.DataFrame:
	"""Return sleep rows with parsed start/stop times and sorting by start."""
	if df_sleep.empty:
		return pd.DataFrame(columns=["night", "start", "stop"])

	df = df_sleep.copy()
	df["start"] = pd.to_datetime(df.get("start"), errors="coerce")
	df["stop"] = pd.to_datetime(df.get("stop"), errors="coerce")
	if "night" not in df.columns:
		df["night"] = range(len(df))

	df = df.dropna(subset=["start"]).sort_values("start")
	return df[["night", "start", "stop"]]


def _minute_series(df_wristband: pd.DataFrame, wear_col: str | None = None) -> pd.Series:
	"""Return per-minute timestamps where wristband data exists (optionally with wear_col present)."""
	if df_wristband.empty or "datetime" not in df_wristband.columns:
		return pd.Series(dtype="datetime64[ns]")

	df = df_wristband.copy()
	if wear_col and wear_col in df.columns:
		df = df[df[wear_col].notna()]

	minutes = pd.to_datetime(df["datetime"], errors="coerce").dropna().dt.floor("min")
	return minutes


def _coverage_between(minutes: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> float:
	"""Compute minute coverage between [start, end) as observed/expected."""
	if pd.isna(start) or pd.isna(end) or end <= start:
		return 0.0

	window_minutes = minutes[(minutes >= start) & (minutes < end)]
	observed = window_minutes.nunique()
	expected = math.ceil((end - start).total_seconds() / 60)
	if expected <= 0:
		return 0.0
	return float(observed) / float(expected)


def _day_windows_after_nights(df_sleep: pd.DataFrame) -> list[dict[str, pd.Timestamp]]:
	"""Build day intervals following each night.

	The window starts at the night's stop (fallback to start) and ends at the
	next night's start when available; otherwise it ends 18 hours after the
	current night start/stop. When two nights exist, the full gap is used even
	if it exceeds 18 hours.
	"""
	windows = _sleep_windows(df_sleep)
	result: list[dict[str, pd.Timestamp]] = []
	if windows.empty:
		return result

	rows = windows.reset_index(drop=True)
	for idx, row in rows.iterrows():
		start_anchor = row.get("stop") if pd.notna(row.get("stop")) else row.get("start")

		if idx + 1 < len(rows):
			end_anchor = rows.loc[idx + 1, "start"]
		else:
			end_anchor = start_anchor + pd.Timedelta(hours=18) if pd.notna(start_anchor) else pd.NaT

		# ensure window is forward in time; fall back to +18h if malformed
		if pd.isna(end_anchor) or (pd.notna(start_anchor) and end_anchor <= start_anchor):
			end_anchor = start_anchor + pd.Timedelta(hours=18) if pd.notna(start_anchor) else pd.NaT

		result.append(
			{
				"night": row.get("night"),
				"start": start_anchor,
				"end": end_anchor,
				"period_label": "night_following_day",
			}
		)

	return result


def _day_windows_before_nights(df_sleep: pd.DataFrame) -> list[dict[str, pd.Timestamp]]:
	"""Build day intervals leading into each night.

	When a previous night exists, the window starts at that night's stop
	(fallback to start) and ends at the current night start. If no previous
	night is available, the window starts 18 hours before the current night
	start. This mirrors the definition "between two nights or max 18 hours
	before the night when the earlier night is missing".
	"""
	windows = _sleep_windows(df_sleep)
	result: list[dict[str, pd.Timestamp]] = []
	if windows.empty:
		return result

	rows = windows.reset_index(drop=True)
	for idx, row in rows.iterrows():
		end_anchor = row.get("start")

		if idx - 1 >= 0:
			prev = rows.loc[idx - 1]
			start_anchor = prev.get("stop") if pd.notna(prev.get("stop")) else prev.get("start")
			if pd.isna(start_anchor) or (pd.notna(end_anchor) and start_anchor >= end_anchor):
				start_anchor = (end_anchor - pd.Timedelta(hours=18)) if pd.notna(end_anchor) else pd.NaT
		else:
			start_anchor = (end_anchor - pd.Timedelta(hours=18)) if pd.notna(end_anchor) else pd.NaT

		result.append(
			{
				"night": row.get("night"),
				"start": start_anchor,
				"end": end_anchor,
				"period_label": "day_before_night",
			}
		)

	return result


def _boundary_day_windows(df_sleep: pd.DataFrame) -> list[dict[str, pd.Timestamp]]:
	"""Build additional day windows before the first night."""
	windows = _sleep_windows(df_sleep)
	result: list[dict[str, pd.Timestamp]] = []
	if windows.empty:
		return result

	rows = windows.reset_index(drop=True)
	first = rows.iloc[0]

	# Before the first night (18h leading in)
	first_start = first.get("start")
	if pd.notna(first_start):
		result.append(
			{
				"night": first.get("night"),
				"start": first_start - pd.Timedelta(hours=18),
				"end": first_start,
				"period_label": "before_first_night",
			}
		)

	return result


def nights_with_following_wristband_day(
	df_sleep: pd.DataFrame,
	df_wristband: pd.DataFrame,
	*,
	wear_col: str | None = None,
	coverage_threshold: float = 0.7,
) -> tuple[int, pd.DataFrame]:
	"""Count nights whose following day window meets a coverage threshold.

	Parameters
	----------
	df_sleep: pd.DataFrame
		Sleep report frame containing at least `start` (and optionally `stop` / `night`).
	df_wristband: pd.DataFrame
		Wristband per-minute frame containing `datetime` and optional `wear_col`.
	wear_col: str | None
		Column name to require non-null wearing-detection values when computing coverage.
	coverage_threshold: float
		Fraction in (0,1] that the observed minutes must reach within the defined
		day window to be counted (default 0.7 for 70%).

	Returns
	-------
	(int, pd.DataFrame)
		Number of nights meeting the threshold and a dataframe with per-night coverage
		values (columns: `night`, `start`, `end`, `coverage`).
	"""
	minutes = _minute_series(df_wristband, wear_col)
	day_windows = _day_windows_after_nights(df_sleep)
	if not len(day_windows):
		return 0, pd.DataFrame(columns=["night", "start", "end", "coverage"])

	records: list[dict[str, object]] = []
	for window in day_windows:
		cov = _coverage_between(minutes, window["start"], window["end"])
		window_record = {**window, "coverage": cov}
		records.append(window_record)

	matched = pd.DataFrame.from_records(records)
	matched = matched[matched["coverage"] >= coverage_threshold]
	matched = matched.sort_values("start") if not matched.empty else matched
	return len(matched), matched


def wristband_days_with_following_sleep_night(
	df_sleep: pd.DataFrame,
	df_wristband: pd.DataFrame,
	*,
	wear_col: str | None = None,
	coverage_threshold: float = 0.7,
) -> tuple[int, pd.DataFrame]:
	"""Count day windows preceding nights that meet a coverage threshold.

	Parameters
	----------
	df_sleep: pd.DataFrame
		Sleep report frame containing at least `start` (and optionally `stop` / `night`).
	df_wristband: pd.DataFrame
		Wristband per-minute frame containing `datetime` and optional `wear_col`.
	wear_col: str | None
		Column name to require non-null wearing-detection values when computing coverage.
	coverage_threshold: float
		Fraction in (0,1] that the observed minutes must reach within the defined
		day window to be counted (default 0.7 for 70%).

	Returns
	-------
	(int, pd.DataFrame)
		Number of day windows meeting the threshold and a dataframe with per-window
		coverage values (columns: `night`, `start`, `end`, `coverage`).
	"""
	minutes = _minute_series(df_wristband, wear_col)
	day_windows = _day_windows_before_nights(df_sleep)
	if not len(day_windows):
		return 0, pd.DataFrame(columns=["night", "start", "end", "coverage"])

	records: list[dict[str, object]] = []
	for window in day_windows:
		cov = _coverage_between(minutes, window["start"], window["end"])
		window_record = {**window, "coverage": cov}
		records.append(window_record)

	matched = pd.DataFrame.from_records(records)
	matched = matched[matched["coverage"] >= coverage_threshold]
	matched = matched.sort_values("start") if not matched.empty else matched
	return len(matched), matched


def night_day_summary_table(
	df_sleep: pd.DataFrame,
	df_wristband: pd.DataFrame,
	*,
	wear_col: str | None = None,
	coverage_threshold: float = 0.7,
) -> pd.DataFrame:
	"""Per-night table combining night duration and day coverage metrics.

	Parameters
	----------
	df_sleep: pd.DataFrame
		Sleep report frame containing at least `start` (and optionally `stop` / `night`).
	df_wristband: pd.DataFrame
		Wristband per-minute frame containing `datetime` and optional `wear_col`.
	wear_col: str | None
		Column name to require non-null wearing-detection values when computing coverage.
	coverage_threshold: float
		Fraction in (0,1] used to flag `meets_threshold` in the returned table
		(default 0.7 for 70%).

	Returns
	-------
	pd.DataFrame
		Rows per defined day window; columns include night times, night duration,
		coverage metrics (`day_minutes_observed`, `day_minutes_expected`, `day_coverage`),
		`meets_threshold`, and `period_label` indicating whether the row is the
		usual following-day window or a boundary window (e.g., `before_first_night`).
	"""
	minutes = _minute_series(df_wristband, wear_col)
	day_windows = _day_windows_after_nights(df_sleep)
	day_windows = day_windows + _boundary_day_windows(df_sleep)
	if not len(day_windows):
		return pd.DataFrame(
			columns=[
				"night",
				"night_start",
				"night_stop",
				"night_duration_minutes",
				"night_duration_hours",
				"day_start",
				"day_end",
				"day_minutes_observed",
				"day_minutes_expected",
				"day_coverage",
				"meets_threshold",
				"period_label",
			]
		)

	sleep_rows = _sleep_windows(df_sleep).set_index("night")
	records: list[dict[str, object]] = []

	for window in day_windows:
		night_id = window.get("night")
		night_row = sleep_rows.loc[night_id] if night_id in sleep_rows.index else None
		night_start = night_row["start"] if night_row is not None else pd.NaT
		night_stop = night_row["stop"] if night_row is not None else pd.NaT

		night_dur_min = None
		if pd.notna(night_start) and pd.notna(night_stop) and night_stop > night_start:
			night_dur_min = int((night_stop - night_start).total_seconds() // 60)

		obs, exp, cov = _window_stats(minutes, window["start"], window["end"])

		records.append(
			{
				"night": night_id,
				"night_start": night_start,
				"night_stop": night_stop,
				"night_duration_minutes": night_dur_min,
				"night_duration_hours": (night_dur_min / 60.0) if night_dur_min is not None else None,
				"day_start": window["start"],
				"day_end": window["end"],
				"day_minutes_observed": obs,
				"day_minutes_expected": exp,
				"day_coverage": cov,
				"meets_threshold": cov >= coverage_threshold,
				"period_label": window.get("period_label", "night_following_day"),
			}
		)

	df = pd.DataFrame.from_records(records)
	return df.sort_values("night_start") if not df.empty else df


__all__ = [
	"nights_with_following_wristband_day",
	"wristband_days_with_following_sleep_night",
	"night_day_summary_table",
]