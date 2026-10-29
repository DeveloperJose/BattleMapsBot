function totalPMGain() {
    const total = this.dmgInfos.reduce((acc, v) => [
        acc[0]
        + v.maxCounterInfo.maxLuck.counterFundsDamage
        + (v.maxInfo.fundsDamage / 2),
        acc[1]
        + v.minCounterInfo.minLuck.counterFundsDamage
        + (v.minInfo.fundsDamage / 2),
    ], [0, 0]);
    return JSON.stringify(total);
}
