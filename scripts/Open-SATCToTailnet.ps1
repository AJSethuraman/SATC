# Make the SATC practice-ops app reachable from AJ's own devices over Tailscale.
#
# AUTHORISED BY AJ, 5 October 2026: "we are setting up bookkeeping to work
# through tailscale and i can view it on the same network, this is a control i'm
# comfortable with. leaving my environment is not conducive to it leaving only
# the forge."
#
# WHAT THIS DOES AND DOES NOT DO. It adds ONE inbound firewall rule, scoped to
# the Tailscale address ranges only -- the same shape as the existing
# "Forge - Open WebUI (Tailnet only)" and "Forge - Netdata (Tailnet only)" rules.
# It does not touch Remote Desktop, Ollama, or any other rule.
#
# THE APP HAS NO LOGIN. This rule plus the app's own host allowlist are the
# entire control. Anything that can reach 100.125.166.122:5050 is in, and the
# screens behind it hold real client names.
#
# Run from an ADMINISTRATOR PowerShell. Creating a firewall rule needs it.

$ErrorActionPreference = 'Stop'
$name = 'Forge - SATC Tax Processor (Tailnet only)'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
      ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Error "Not elevated. Right-click PowerShell -> Run as administrator, then run this again."
  exit 1
}

if (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue) {
  Write-Host "  Rule already exists. Nothing to create."
} else {
  New-NetFirewallRule -DisplayName $name `
    -Description 'SATC practice-ops app on 5050, Tailnet-scoped. NO LOGIN - this rule and the app host allowlist are the whole control. Authorised by AJ 2026-10-05.' `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5050 `
    -RemoteAddress '100.64.0.0/10', 'fd7a:115c:a1e0::/48' `
    -Profile Any -Enabled True | Out-Null
  Write-Host "  Rule created."
}

# VERIFIED BY READING IT BACK, not by trusting the command above. A firewall
# cmdlet that fails under a non-elevated shell has already printed "created"
# once in this project's history because the script carried on past the error.
$r = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
if (-not $r) { Write-Error "Rule is NOT present after creating it. Stop and look."; exit 1 }
$p = $r | Get-NetFirewallPortFilter
$a = $r | Get-NetFirewallAddressFilter
Write-Host ""
Write-Host "  name    : $($r.DisplayName)"
Write-Host "  enabled : $($r.Enabled)   action: $($r.Action)   profile: $($r.Profile)"
Write-Host "  port    : $($p.Protocol)/$($p.LocalPort)"
Write-Host "  remote  : $($a.RemoteAddress -join ' | ')"
Write-Host ""
Write-Host "  Next: restart the app so it binds beyond loopback --"
Write-Host "        scripts\Start-SATCOnTailnet.cmd"
