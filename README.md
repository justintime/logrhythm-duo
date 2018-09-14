# logrhythm-duo - Import Duo MFA logs into LogRhythm

The code in this project is heavily based on the example provided by the [duo_client module](https://github.com/duosecurity/duo_client_python/tree/master/examples/splunk).
I cleaned up a few things here and there, but the biggest difference is that the script now logs the messages to individual log files, of which are rotated nightly and 
kept for 7 days.  This helps ensure that no logs are lost due to truncation, etc, while also ensuring it doesn't eventually fill up the disk.

This script is intended to be run from any operating system that can run Python.  Use cron on Linux #TODO document this, or a scheduled task on Windows #TODO powershell?.

## Configure Duo

Setup the Duo side of things by following the "First Steps" section at https://duo.com/docs/splunkapp

## Configure this script

``` bash
pip install --requirement requirements.txt
```