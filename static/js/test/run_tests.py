#!/usr/bin/python

import subprocess
import os.path

browsers = [
  "firefox",
  "ie6",
]

def main():
  test_page = "http://localhost:8081/static/js/test/Test_Luminotes.html"
  test_runner = "http://localhost:8081/static/jsunit/testRunner.html?testpage=%s&autorun=true" % test_page

  # launch tests in each supported browser
  for browser in browsers:
    subprocess.call( [ browser, test_runner ] )


if __name__ == "__main__":
  main()
