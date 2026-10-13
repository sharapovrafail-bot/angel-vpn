sc stop AmneziaWGTunnel$AngelVPN
sc delete AmneziaWGTunnel$AngelVPN
taskkill /IM "AngelVPN-service.exe" /F
taskkill /IM "AngelVPN.exe" /F
exit /b 0
