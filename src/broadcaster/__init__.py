"""Proactive weather-based caring broadcast for TCM-Jessica.

Jessica sends a caring TCM health tip to active users when HK weather
has a notable condition (cold front, heatwave, rainstorm, humidity+heat).

Cap: each individual user receives at most 2 broadcasts per ISO week,
with a minimum 36-hour gap between them.
"""
