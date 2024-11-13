import argparse
import ipaddress
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from DrissionPage import ChromiumPage, ChromiumOptions
from pyvirtualdisplay import Display

from CloudflareBypasser import CloudflareBypasser

app = FastAPI()
enable_log = True


# Pydantic model for the response
class ClientRequest(BaseModel):
    cmd: str = None
    cookies: list = None
    maxTimeout: int = None
    url: str = None
    postData: str = None


class Solution(BaseModel):
    url: str = None
    status: int = None
    response: str = None
    cookies: list = None
    userAgent: str = None


class ClientResponse(BaseModel):
    status: str = None
    message: str = ""
    version: str = "1.0.0"
    solution: Solution = None


# Function to check if the URL is safe
def is_safe_url(url: str) -> bool:
    parsed_url = urlparse(url)
    safe = True
    if parsed_url.hostname == 'localhost' or parsed_url.scheme == "file":
        safe = False
    else:
        try:
            ip_obj = ipaddress.ip_address(parsed_url.hostname)
            safe = not ip_obj.is_private
        except ValueError:
            pass
    return safe


# Function to bypass Cloudflare protection
def bypass_cloudflare(url: str, retries: int, enable_log: bool) -> ChromiumPage:
    options = ChromiumOptions()
    options.set_paths(browser_path="/usr/bin/chromium-browser").headless(False).auto_port()
    options.set_argument("--no-sandbox")  # Necessary for Docker
    options.set_argument("--disable-gpu")  # Optional, helps in some cases

    driver = ChromiumPage(addr_or_opts=options)
    try:
        driver.listen.start(targets=url)
        driver.get(url)
        cf_bypasser = CloudflareBypasser(driver, retries, enable_log)
        cf_bypasser.bypass()
        return driver
    except Exception as e:
        driver.quit()
        raise e


# Endpoint to get Solver response
@app.post("/v1")
async def get_solverr(request: ClientRequest):
    if not is_safe_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        if request.cmd == "request.get":
            # Start Xvfb for Docker
            display = Display(visible=0, size=(1920, 1080))
            display.start()

            # Start bypass
            driver = bypass_cloudflare(request.url, 5, enable_log)
            packet = driver.listen.wait()
            driver.listen.stop()
            cookies = driver.cookies(as_dict=False)

            # Build response
            res = ClientResponse()
            res.status = "ok"
            res.solution = Solution(
                url=packet.response.url,
                status=packet.response.status,
                response=driver.html,
                userAgent=driver.user_agent,
                cookies=cookies,
            )

            driver.quit()
            display.stop()  # Stop Xvfb

            return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cloudflare bypass api")
    parser.add_argument("--nolog", action="store_false", help="Disable logging")

    args = parser.parse_args()
    enable_log = args.nolog

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
