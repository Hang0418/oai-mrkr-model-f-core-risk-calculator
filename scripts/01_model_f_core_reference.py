#!/usr/bin/env python3
"""Dependency-free reference implementation of Model F-core."""

from __future__ import annotations

import argparse
import math


BETA = {
    "age": 0.00164077477256476,
    "female": -0.13583783214975,
    "right_knee": 0.00441591384434222,
    "pain_z": 0.290861790566034,
    "baseline_kl": 0.778457697796415,
    "kl_worsening": 1.01942211707925,
}
OAI_PAIN_MEAN = 1.40536404639175
OAI_PAIN_SD = 1.73779647077576
MRKR_PAIN_MEAN = 3.37631887456038
MRKR_PAIN_SD = 3.39454813926584
OAI_H0_24 = 0.00391871810230842
MRKR_H0_24 = 0.0705638786413772
MRKR_GAMMA = 0.681400186474898


def linear_predictor(age, female, right_knee, pain, baseline_kl, month24_kl, pain_mean, pain_sd):
    pain_z = (pain - pain_mean) / pain_sd
    kl_worsening = int(month24_kl - baseline_kl >= 1)
    lp = (
        BETA["age"] * age
        + BETA["female"] * female
        + BETA["right_knee"] * right_knee
        + BETA["pain_z"] * pain_z
        + BETA["baseline_kl"] * baseline_kl
        + BETA["kl_worsening"] * kl_worsening
    )
    return lp, pain_z, kl_worsening


def cox_risk(h0, lp):
    return 1.0 - math.exp(-h0 * math.exp(lp))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--age", type=float, required=True)
    parser.add_argument("--female", type=int, choices=[0, 1], required=True)
    parser.add_argument("--right-knee", type=int, choices=[0, 1], required=True)
    parser.add_argument("--pain", type=float, required=True)
    parser.add_argument("--baseline-kl", type=int, choices=range(5), required=True)
    parser.add_argument("--month24-kl", type=int, choices=range(5), required=True)
    parser.add_argument("--mode", choices=["oai", "mrkr", "both"], default="both")
    args = parser.parse_args()

    lp_oai, z_oai, worsening = linear_predictor(
        args.age, args.female, args.right_knee, args.pain,
        args.baseline_kl, args.month24_kl, OAI_PAIN_MEAN, OAI_PAIN_SD,
    )
    lp_mrkr, z_mrkr, _ = linear_predictor(
        args.age, args.female, args.right_knee, args.pain,
        args.baseline_kl, args.month24_kl, MRKR_PAIN_MEAN, MRKR_PAIN_SD,
    )
    if args.mode in {"oai", "both"}:
        print(f"OAI pain z: {z_oai:.6f}")
        print(f"OAI LP: {lp_oai:.6f}")
        print(f"Original OAI 24-month risk: {cox_risk(OAI_H0_24, lp_oai):.6%}")
    if args.mode in {"mrkr", "both"}:
        print(f"MRKR pain z: {z_mrkr:.6f}")
        print(f"MRKR LP: {lp_mrkr:.6f}")
        print(f"Apparent MRKR 24-month hardware-detection risk: {cox_risk(MRKR_H0_24, MRKR_GAMMA * lp_mrkr):.6%}")
    print(f"KL worsening: {worsening}")


if __name__ == "__main__":
    main()
