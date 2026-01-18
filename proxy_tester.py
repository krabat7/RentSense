import asyncio
import aiohttp
import time
from urllib.parse import urlparse
import random

PROXIES = [
    "http://8MossJ:N1qR7a@194.67.223.202:9869",
    "http://8MossJ:N1qR7a@194.67.220.233:9107",
    "http://8MossJ:N1qR7a@194.67.221.111:9954",
    "http://8MossJ:N1qR7a@194.67.219.210:9263",
    "http://HdGfox:1gwbaf@213.139.222.248:9855",
    "http://HdGfox:1gwbaf@213.139.221.254:9642",
    "http://HdGfox:1gwbaf@213.139.222.180:9878",
    "http://HdGfox:1gwbaf@213.139.221.88:9066",
    "http://LMT8Lo:E7Bjut@178.171.43.220:9809",
    "http://LMT8Lo:E7Bjut@178.171.42.247:9665",
    "http://dBJDq9:kjwyCA@23.236.132.231:9410",
    "http://dBJDq9:kjwyCA@23.229.42.223:9498",
    "http://EPaDhwK2Vg:sHbPMMYxcQ@31.184.243.54:38479",
    "http://SeHvwxXK9g:Pr795Xreg6@46.161.31.185:38432",
    "http://4D7D7f:mE9cRE@213.139.222.69:9010",
    "http://4D7D7f:mE9cRE@213.139.222.149:9516",
    "http://4D7D7f:mE9cRE@213.139.223.145:9193",
    "http://4D7D7f:mE9cRE@213.139.222.227:9625",
    "http://HrkB8A:GoTkpe@212.102.145.24:9687",
    "http://HrkB8A:GoTkpe@212.102.144.77:9656",
    "http://HrkB8A:GoTkpe@178.171.43.146:9912",
    "http://okJ0KF:9LmuSc@194.67.219.124:9425",
    "http://okJ0KF:9LmuSc@194.67.222.245:9817",
    "http://okJ0KF:9LmuSc@194.67.223.76:9814",
    "http://okJ0KF:9LmuSc@194.67.219.15:9043",
    "http://4MfBTo:mgCBFh@31.44.190.147:9657",
    "http://4MfBTo:mgCBFh@194.67.219.3:9623",
    "http://4MfBTo:mgCBFh@194.28.210.85:9963",
    "http://4MfBTo:mgCBFh@194.28.208.50:9743",
    "http://PT9p16:nNmkU8@158.46.182.34:8000",
    "http://MFDsV2:geHwTP@91.233.20.141:8000",
    "http://9D1pZg:a5YoGL@46.19.71.145:8000",
    "http://ftXS76:q5P4rE@147.45.86.232:8000",
    "http://f0muLE:KP4hV2@195.64.101.45:8000"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/123.0",
]

async def test_proxy(session, proxy, test_url="https://www.google.com"):
    """Асинхронная проверка одного прокси."""
    parsed = urlparse(proxy)
    proxy_auth = aiohttp.BasicAuth(parsed.username, parsed.password) if parsed.username else None
    proxy_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    
    try:
        start = time.time()
        async with session.get(test_url, proxy=proxy_url, proxy_auth=proxy_auth, headers=headers, timeout=15, ssl=False) as resp:
            latency = int((time.time() - start) * 1000)
            if resp.status == 200:
                return proxy, True, latency, resp.status, "OK"
            else:
                return proxy, False, latency, resp.status, f"HTTP {resp.status}"
    except asyncio.TimeoutError:
        return proxy, False, 15000, None, "Timeout"
    except aiohttp.ClientConnectorError:
        return proxy, False, 0, None, "Connection Failed"
    except aiohttp.ClientProxyConnectionError:
        return proxy, False, 0, None, "Proxy Auth/Connection Error"
    except Exception as e:
        return proxy, False, 0, None, f"Error: {str(e)[:50]}"

async def main():
    print("🔍 Начинаю осторожную проверку прокси...\n")
    print(f"Всего прокси для проверки: {len(PROXIES)}")
    print("="*70)
    
    connector = aiohttp.TCPConnector(limit=5)  # Не более 5 одновременных соединений
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for proxy in PROXIES:
            # Случайная задержка между запуском проверок (0.5-3 сек)
            await asyncio.sleep(random.uniform(0.5, 3))
            tasks.append(test_proxy(session, proxy))
        
        results = await asyncio.gather(*tasks)
    
    working = []
    dead = []
    
    for proxy, is_ok, latency, status, msg in results:
        if is_ok:
            working.append((proxy, latency))
            print(f"✅ {proxy[:50]:<50} | Задержка: {latency:>4}ms | Статус: {msg}")
        else:
            dead.append((proxy, msg))
            print(f"❌ {proxy[:50]:<50} | Ошибка: {msg}")
    
    print("="*70)
    print(f"\n📊 Итоги:")
    print(f"   Рабочих: {len(working)}")
    print(f"   Не рабочих: {len(dead)}")
    
    if working:
        print(f"\n🚀 Топ-5 самых быстрых рабочих прокси:")
        for proxy, latency in sorted(working, key=lambda x: x[1])[:5]:
            print(f"   • {proxy[:60]}... ({latency}ms)")
    
    # Сохраняем результаты в файл
    with open('proxy_results.txt', 'w') as f:
        f.write("Рабочие прокси:\n")
        for proxy, latency in working:
            f.write(f"{proxy} | {latency}ms\n")
        
        f.write("\nНе рабочие прокси:\n")
        for proxy, msg in dead:
            f.write(f"{proxy} | {msg}\n")
    
    print("\n💾 Результаты сохранены в файл proxy_results.txt")

if __name__ == "__main__":
    asyncio.run(main())