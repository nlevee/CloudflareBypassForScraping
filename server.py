import json
import re
import os
from urllib.parse import urlparse

from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import Dict
import argparse

browser_path = "/usr/bin/google-chrome"
app = FastAPI()
log = True

# Pydantic model for the response
class V1RequestBase(BaseModel):
    # V1RequestBase
    cmd: str = None
    cookies: list = None
    maxTimeout: int = None
    proxy: dict = None
    session: str = None
    session_ttl_minutes: int = None

    # V1Request
    url: str = None
    postData: str = None
    returnOnlyCookies: bool = None

class ChallengeResolutionResultT(BaseModel):
    url: str = None
    status: int = None
    headers: dict = None
    response: str = None
    cookies: list = None
    userAgent: str = None
        
class V1ResponseBase(BaseModel):
    # V1ResponseBase
    status: str = None
    message: str = ""
    session: str = None
    sessions: list[str] = None
    startTimestamp: int = None
    endTimestamp: int = None
    version: str = "1.0.0"

    # V1ResponseSolution
    solution: ChallengeResolutionResultT = None


# Function to check if the URL is safe
def is_safe_url(url: str) -> bool:
    parsed_url = urlparse(url)
    ip_pattern = re.compile(
        r"^(127\.0\.0\.1|localhost|0\.0\.0\.0|::1|10\.\d+\.\d+\.\d+|172\.1[6-9]\.\d+\.\d+|172\.2[0-9]\.\d+\.\d+|172\.3[0-1]\.\d+\.\d+|192\.168\.\d+\.\d+)$"
    )
    hostname = parsed_url.hostname
    if (hostname and ip_pattern.match(hostname)) or parsed_url.scheme == "file":
        return False
    return True


# Function to bypass Cloudflare protection
def bypass_cloudflare(url: str, retries: int, log: bool) -> ChromiumPage:
    from pyvirtualdisplay import Display

    # Start Xvfb for Docker
    display = Display(visible=0, size=(1920, 1080))
    display.start()

    options = ChromiumOptions()
    options.set_argument("--no-sandbox")  # Necessary for Docker
    options.set_argument("--disable-gpu")  # Optional, helps in some cases
    options.set_paths(browser_path=browser_path).headless(False)

    driver = ChromiumPage(addr_or_opts=options)
    try:
        driver.listen.start(targets=url)
        driver.get(url)
        cf_bypasser = CloudflareBypasser(driver, retries, log)
        cf_bypasser.bypass()
        return driver
    except Exception as e:
        driver.quit()
        display.stop()  # Stop Xvfb
        raise e

# Endpoint to get HTML content and cookies
@app.post("/v1")
async def get_solverr(request: V1RequestBase):
    if not is_safe_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        if request.cmd == "request.get":
            driver = bypass_cloudflare(request.url, 5, log)
            res = driver.listen.wait()
            cookies = driver.cookies(as_dict=False)
            
            sol = ChallengeResolutionResultT()
            sol.url = res.response.url
            sol.headers = dict(res.response.headers.lower_items())
            sol.status = res.response.status
            sol.response = driver.html
            sol.userAgent = driver.user_agent
            sol.cookies = cookies

            driver.quit()

            res = V1ResponseBase()
            res.status = "ok"
            res.solution = sol

            return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cloudflare bypass api")

    parser.add_argument("--nolog", action="store_true", help="Disable logging")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    args = parser.parse_args()
    if args.nolog:
        log = False
    else:
        log = True
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
