  killBtn.onclick = function () {
    swapClickedClass(killBtn, deathBtn);
    swapStats(killStore, totalKillValue);
  };

  deathBtn.onclick = function () {
    swapClickedClass(deathBtn, killBtn);
    swapStats(deathStore, totalDeathValue);
  };