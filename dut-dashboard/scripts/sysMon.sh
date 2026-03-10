#!/bin/ash
# sys_Monitor_mod.sh - Modular snapshot monitor (BusyBox ash)
# Version: v1.3a
# Usage: sys_Monitor_mod.sh <step_time> <duration>
# Example: sys_Monitor_mod.sh 30s 3m

set -u
IFACE_ETH="eth1"
IFACE_WIFI_LIST="ath7 ath16 ath23 ath0 ath1 ath2 ath3 ath4 ath5 ath6 ath8 ath9 ath10 ath11 ath12 ath13 ath14 ath15 ath17 ath18 ath19 ath20 ath21 ath22"
PATH=$PATH:/sbin:/usr/sbin

usage() {
  echo "Usage: $0 <step_time> <duration>"
  echo "  <step_time>: Ns | Nm | Nh"
  echo "  <duration> : Ns | Nm | Nh"
  exit 1
}

to_seconds() {
  local v="$1" num mult
  case "$v" in
    *s) num="${v%s}"; mult=1 ;;
    *m) num="${v%m}"; mult=60 ;;
    *h) num="${v%h}"; mult=3600 ;;
    *)  echo "ERR"; return 1 ;;
  esac
  case "$num" in
    ''|*[!0-9]*) echo "ERR"; return 1 ;;
  esac
  echo $(( num * mult ))
}

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

run() {
  echo "----- $* -----"
  "$@" 2>&1
  echo ""
}

# 1) CPU Utilization
cpu_utilization() {
  local S1="/tmp/procstat1_$$" S2="/tmp/procstat2_$$"
  echo "=== CPU Utilization ================================================================="
  grep '^cpu' /proc/stat > "$S1"
  sleep 1
  grep '^cpu' /proc/stat > "$S2"

  awk '
    function pct(part, tot) { return (tot>0)? (part*100.0/tot) : 0.0 }
    NR==FNR { for (i=2;i<=NF;i++) a[FNR,i]=$i; next }
    {
      for (i=2;i<=NF;i++) d[i]=$i - a[FNR,i]
      tot=0; for (i=2;i<=NF;i++) tot+=d[i]
      user=d[2]; nicev=d[3]; sysv=d[4]; idle=d[5]; iow=d[6]; irq=d[7]; sirq=d[8]
      if (FNR>1) {
        idx=FNR-2
        printf("CPU%d: %5.1f%% usr %5.1f%% sys %5.1f%% nic %5.1f%% idle %5.1f%% io %5.1f%% irq %5.1f%% sirq\n",
               idx, pct(user,tot), pct(sysv,tot), pct(nicev,tot), pct(idle,tot), pct(iow,tot), pct(irq,tot), pct(sirq,tot))
      }
    }
  ' "$S1" "$S2"
  rm -f "$S1" "$S2"
  echo ""
}

# 1.1) CPU hog process / thread (top -H)
cpu_hotspot() {
  echo "=== CPU Hotspot (top threads by %CPU) ==============================================="
  # 優先用 top -H -b -n 1；不支援時 fallback
  if top -H -b -n 1 2>/dev/null | head -40; then
    :
  elif top -H -n 1 2>/dev/null | head -40; then
    :
  elif top -b -n 1 2>/dev/null | head -40; then
    :
  else
    # 最差情況：沒有 -b/-H，就盡量抓一份 top 輸出
    top -n 1 2>/dev/null | head -40
  fi
  echo ""
}

# 2) Memory Utilization
memory_utilization() {
  echo "=== Memory Utilization (/proc/meminfo) =============================================="
  run cat /proc/meminfo
}

# 3) Disk Utilization
disk_utilization() {
  echo "=== Disk Utilization (df) ==========================================================="
  run df
}

# 4) Interface Status（單介面 + 全介面顯示）
interface_status() {
  echo "=== Interface Status ================================================================"
  echo "----- ethtool ${IFACE_ETH} ----------------------------------------------------------"
  ethtool "${IFACE_ETH}" 2>/dev/null | awk -v iface="${IFACE_ETH}" '
    /^[[:space:]]*Speed:/            { speed=$2 }
    /^[[:space:]]*Duplex:/           { duplex=$2 }
    /^[[:space:]]*Port:/             { port=$2 }
    /^[[:space:]]*Auto-negotiation:/ { auto=$2 }
    /^[[:space:]]*Link detected:/    { link=$3 }
    END {
      printf("Uplink Port Interface: %s | Speed: %s | Duplex: %s | Port: %s | Auto-negotiation: %s | Link detected: %s\n",
             iface, speed, duplex, port, auto, link)
    }
  '
  echo ""
  echo "----- ifconfig (all interfaces) -----------------------------------------------------"
  ifconfig
  echo ""
}

# 5) Wi-Fi Status
wifi_status() {
  echo "=== Wi-Fi Status (iwconfig) ========================================================="
  iwconfig 2>/dev/null | awk '
    /^[^[:space:]]/ {
      if (block && output) print block;
      block=$0 "\n"; output=1; next
    }
    /no wireless extensions/ {
      block=""; output=0; next
    }
    { block = block $0 "\n" }
    END { if (block && output) print block }
  '
  echo ""
}

# 6) CURL Hooks（REST 查詢）
run_curl() {
  curl -k "$1"
  echo ""
  sleep 1
}

curl_hooks() {
  echo "=== CURL Hooks ======================================================================"
  run_curl "https://127.0.0.1:10443/ap/info/system/basic"
  run_curl "https://127.0.0.1:10443/ap/info/system/advance"
  run_curl "https://127.0.0.1:10443/ap/info/wireless/basic?radio=2g&ssid_index=0"
  run_curl "https://127.0.0.1:10443/ap/info/wireless/basic?radio=5g&ssid_index=0"
  run_curl "https://127.0.0.1:10443/ap/info/wireless/basic?radio=6g&ssid_index=0"
    
  echo "--- CLIENTS Radio=2G ---"
  run_curl "https://127.0.0.1:10443/ap/info/wireless/clients?Radio=2G"
  echo "--- CLIENTS Radio=5G ---"
  run_curl "https://127.0.0.1:10443/ap/info/wireless/clients?Radio=5G"
  echo "--- CLIENTS Radio=6G ---"
  run_curl "https://127.0.0.1:10443/ap/info/wireless/clients?Radio=6G"
  echo ""
}

# 7) Process Status
process_status() {
  echo "=== Process Status (VSZ != 0) ======================================================="
  ps | awk 'NR==1 || $3 != 0'
  echo ""
}

# 8) Process Details
process_details_all() {
  echo "=== Process Details ================================================================="
  for P in /proc/[0-9]*; do
    [ -f "$P/status" ] || continue
    pid="${P##*/}"
    awk '
      /^Name:/   { name=$2 }
      /^VmSize:/ { vmsize=$2" "$3 }
      /^VmRSS:/  { vmrss=$2" "$3 }
      /^VmData:/ { vmdata=$2" "$3 }
      /^VmSwap:/ { vmswap=$2" "$3 }
      /^Threads:/ { threads=$2 }
      /^Cpus_allowed_list:/ { cpu=$2 }
      /^voluntary_ctxt_switches:/ { vol=$2 }
      /^nonvoluntary_ctxt_switches:/ { nonvol=$2 }
      END {
        if (vmsize != "" && vmsize != "0 kB") {
          printf("Process: %-15s | PID: %-5s | VmSize: %-10s | VmRSS: %-10s | VmData: %-10s | VmSwap: %-8s | Threads: %-4s | CPU: %-4s | vol_ctxt: %-8s | nonvol_ctxt: %-8s\n",
                 name, pid, vmsize, vmrss, vmdata, vmswap, threads, cpu, vol, nonvol)
        }
      }
    ' pid="$pid" "$P/status"
  done
  echo ""
}

# 9) Wi-Fi Client List
wifi_client_list_all() {
  echo "=== Wi-Fi Client List ==============================================================="
  for IFACE_WIFI in $IFACE_WIFI_LIST; do
    wlanconfig "${IFACE_WIFI}" list 2>/dev/null | awk -v iface="${IFACE_WIFI}" '
      /^ADDR[[:space:]]/ { next }
      /^[0-9a-fA-F:]{17}/ {
        assoc_time = ""
        for (i=1; i<=NF; i++) {
          if ($i ~ /^[0-9]{2}:[0-9]{2}:[0-9]{2}$/) {
            assoc_time = $i
            break
          }
        }
        printf("[%s] | ADDR: %s | CHAN: %s | TXRATE: %s | RXRATE: %s | RSSI: %s | IDLE: %s | ASSOCTIME: %s\n",
               iface, $1, $3, $4, $5, $6, $10, assoc_time)
      }
    '
  done
  echo ""
}

# 10) Interrupt & SoftIRQ Analysis
interrupt_softirq_analysis() {
  local I1="/tmp/interrupts1_$$" I2="/tmp/interrupts2_$$"
  local S1="/tmp/softirqs1_$$" S2="/tmp/softirqs2_$$"

  echo "=== Interrupt / SoftIRQ Hotspot (Δ=1s) ============================================="

  # snapshot 1
  cat /proc/interrupts > "$I1" 2>/dev/null || return 0
  cat /proc/softirqs > "$S1" 2>/dev/null || true
  sleep 1
  # snapshot 2
  cat /proc/interrupts > "$I2" 2>/dev/null || return 0
  cat /proc/softirqs > "$S2" 2>/dev/null || true

  echo "--- /proc/interrupts (Top 10 by delta, auto classify WIFI/ETH/OTHER) ---------------"
  awk '
    NR==FNR {
      # base snapshot
      if ($1 ~ /^[0-9]+:/) {
        id=$1
        sum=0
        for (i=2;i<NF;i++) {
          if ($i ~ /^[0-9]+$/) sum+=$i
        }
        base[id]=sum
      }
      next
    }
    $1 ~ /^[0-9]+:/ {
      id=$1
      sum=0
      for (i=2;i<NF;i++) {
        if ($i ~ /^[0-9]+$/) sum+=$i
      }
      delta=sum-base[id]
      if (delta < 0) delta=0
      desc=$NF
      class="OTHER"
      # 粗略分類：Wi-Fi vs Ethernet
      if (desc ~ /ath|wifi|wlan|11ac|11ax|11axg|11axa|mac80211/) class="WIFI"
      else if (desc ~ /eth|gmac|switch|qca8|qca83|qca807|lan|wan/) class="ETH"
      printf("%s %10d %s %s\n", id, delta, class, desc)
    }
  ' "$I1" "$I2" | sort -k2,2nr | head -10

  echo ""
  echo "--- /proc/softirqs (delta per class, sum all CPUs) ---------------------------------"
  awk '
    NR==FNR {
      if ($1 ~ /:$/) {
        key=$1
        gsub(":", "", key)
        sum=0
        for (i=2;i<=NF;i++) if ($i ~ /^[0-9]+$/) sum+=$i
        base[key]=sum
      }
      next
    }
    {
      if ($1 ~ /:$/) {
        key=$1
        gsub(":", "", key)
        sum=0
        for (i=2;i<=NF;i++) if ($i ~ /^[0-9]+$/) sum+=$i
        delta=sum-base[key]
        if (delta < 0) delta=0
        printf("%-8s %12d\n", key, delta)
      }
    }
  ' "$S1" "$S2" | sort -k2,2nr

  echo ""
  rm -f "$I1" "$I2" "$S1" "$S2"
}

# Snapshot Routine
SNAP_COUNT=0
snapshot() {
  SNAP_COUNT=$((SNAP_COUNT + 1))
  echo "====================================================================================="
  echo "= Test Time: $SNAP_COUNT, $(timestamp)                                              ="
  echo "====================================================================================="
  cpu_utilization
  cpu_hotspot           # 新增：抓當下 CPU hog thread
  interrupt_softirq_analysis  # 新增：IRQ / softirq hot spot 分析
  memory_utilization
  disk_utilization
  interface_status
  wifi_status
  curl_hooks
  process_status
  process_details_all
  wifi_client_list_all

  echo ""
  echo ""
}

# ============== Main ==============
[ $# -ne 2 ] && usage

STEP_SEC="$(to_seconds "$1" || true)"
DUR_SEC="$(to_seconds "$2" || true)"

[ "$STEP_SEC" = "ERR" ] || [ "$DUR_SEC" = "ERR" ] && usage
[ "$STEP_SEC" -le 0 ] || [ "$DUR_SEC" -le 0 ] && usage

START_TS="$(date +%s)"
END_TS=$(( START_TS + DUR_SEC ))

echo "Start time: $(timestamp)"
echo "Step: ${1} (${STEP_SEC}s), Duration: ${2} (${DUR_SEC}s)"
echo ""
snapshot

while :; do
  NOW="$(date +%s)"
  [ "$NOW" -ge "$END_TS" ] && break
  sleep "$STEP_SEC" || sleep 1
  snapshot
done

echo "= Test finished @ $(timestamp) ======================================================"
