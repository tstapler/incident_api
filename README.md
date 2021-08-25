# Security Incident API

A security incident API used for a take home interview.

The guidelines can be found in the [INSTRUCTIONS.md](./INSTRUCTIONS.md).

## Project Setup

### Python
Make sure you have a newish version of python. I used to be a fan of pyenv, but I have recently started using ASDF to manage all of my language versions. 
It works pretty well.

I used python 3.8 for this project.
```
❯ python --version
Python 3.8.10
```

Links:
http://asdf-vm.com/guide/getting-started.html#_1-install-dependencies
https://github.com/danhper/asdf-python#install

### Poetry
Poetry is a tool that performs dependency management for python projects. Think something like npm for Javascript or gradle for Java but for python.

You can install poetry on a machine which has python3+ installed using the [following script](https://github.com/python-poetry/poetry#osx--linux--bashonwindows-install-instructions)
```shell
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -
```
## How To

### Running the server

Ensure you have installed `python` and `poetry`, set up the API credentials
by creating a file in the current directory named `.env` with the content:
```
ELEVATE_API_USER={CHANGE_ME}
ELEVATE_API_PASSWORD={CHANGE_ME}
```

After creating the environment file (or setting them manually) should be able to start the server by running `poetry run main.py`

```shell
❯ poetry run python main.py
ujson module not found, using json
msgpack not installed, MsgPackSerializer unavailable
INFO:     Started server process [4124152]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9000 (Press CTRL+C to quit)
```
# Overall Approach

My first approach was to see if I could fetch from all the API endpoints in parallel and return a response within the 2 second time period.

After testing the API it became clear that processing the data realtime would not be a reasonable method for serving this data. There is a section in the [appendix with more information
on the timings I collected.](#external-incident-api-timings-with-curl)

Downloading the incident API endpoints took between 1.75 and 6 seconds per endpoint depending on how much load the external
API was under.

I decided to fetch and aggregate the data from the external incident API using a background job which then stores the calculated data in a cache.

Serving the data pre-calculated from an in memory cache, I was able to get a consistent sub 5ms response time from my server.

# Future Work

To productionize this code there is a laundry list of next steps:

- Figuring out the deployment story for this app. Do we need to dockerize the container and throw it on kubernetes?

- Implement a proper pipeline to get the latest results. Or configure the API to follow a streaming model where 
the events are written to something like Kafka or Apache Pulsar and then processed and added to the DB for the webapp.

- Set up proper persistence (Probably postgres?) and a cache cluster (Redis). The Libraries I used for caching and running cron jobs 
 should happily scale horizontally across multiple instances of the application if we hook up a DB and a cache

- The project needs better logging/telemetry/tracing to let you track the response times over time and find bottlenecks. I used good ol' print because it was easy but in production we'll want better tools. A start would be to actually
configure the python logger and use it.

- We could use some unit tests for this code to verify the conversion logic. In addition, since its network heavy, load testing and chaos testing would be helpful too.

- More documentation for all the methods and some refactoring all over the place

- More product discovery, it will become clear if I made the right tradeoffs after I learn more about the potential usecases for the API.

- What does the user value the most in this application? Latency (lower than 2 second response times) or each call returning the latest data as soon as possible? Since the backend
   API doesn't seem to support gathering all the data over HTTP in real time, we have to make some compromises.

- Should we be storing the incidents that we fetch from the API. The incidents/identies seem to change over time but I 
 ran out of time before I could spend much time investigating if they are completely random or, finite.

- After making a series of requests to the incidents/* and identity apis, there starts to be large numbers of incidents
   where there are no corresponding employee_id for the IPs in the incidents.
   It seems to correlate with load and will reset over time
``` 
... Running for about 1 minute...

Caching incidents
Downloading identities
Downloading incident_data
Completed fetching 2100 incidents with 0 errors

Caching incidents
Downloading identities
Downloading incident_data
Completed fetching 2100 incidents with 0 errors

Caching incidents
Downloading identities
Downloading incident_data
Completed fetching 2100 incidents with 300 errors

Caching incidents
Downloading identities
Downloading incident_data
Completed fetching 2100 incidents with 436 errors

Caching incidents
Downloading identities
Downloading incident_data
Completed fetching 2100 incidents with 900 errors

Caching incidents
Downloading identities
Downloading incident_data
Completed fetching 2100 incidents with 453 errors

Caching incidents
Downloading identities
Downloading incident_data
Completed fetching 2100 incidents with 461 errors

```

# Appendix

### External Incident API Timings with Curl
Just to get some pretty output of how long requests to the incident-api normally take:
```shell
./curltime.sh -u username:password https://incident-api.use1stag.elevatesecurity.io/incidents/probing   
    time_namelookup:  0.000425
       time_connect:  0.070835
    time_appconnect:  0.230084
   time_pretransfer:  0.230535
      time_redirect:  0.304093
 time_starttransfer:  1.749684
                    ----------
         time_total:  1.750229

```

Since our goal was to download everything in 2 seconds and return a response, 1.75 seconds is cutting it close.

Once we start to grab all the endpoints in parallel, the server that's backing them is struggling and that 1.75 second time
slows to somewhere over 4 seconds

```shell
 time xargs -P 0 -I {} ./curltime.sh -u username:password https://incident-api.use1stag.elevatesecurity.io/incidents/{} <<<$'denial\nintrusion\nmisuse\nother\nprobing\nunauthorized\nexecutable'
    time_namelookup:  0.001145
       time_connect:  0.070422
    time_appconnect:  0.228559
   time_pretransfer:  0.228742
      time_redirect:  0.302521
 time_starttransfer:  4.295530
                    ----------
         time_total:  4.364559
    time_namelookup:  0.000510
       time_connect:  0.069288
    time_appconnect:  0.248378
   time_pretransfer:  0.248516
      time_redirect:  0.320352
 time_starttransfer:  4.487618
                    ----------
         time_total:  4.557361
    time_namelookup:  0.000366
       time_connect:  0.069852
    time_appconnect:  0.245948
   time_pretransfer:  0.246069
      time_redirect:  0.319893
 time_starttransfer:  4.553940
                    ----------
         time_total:  4.554054
    time_namelookup:  0.000252
       time_connect:  0.073633
    time_appconnect:  0.249665
   time_pretransfer:  0.249791
      time_redirect:  0.327684
 time_starttransfer:  4.566718
                    ----------
         time_total:  4.639765
    time_namelookup:  0.000368
       time_connect:  0.071006
    time_appconnect:  0.243083
   time_pretransfer:  0.243200
      time_redirect:  0.320025
 time_starttransfer:  4.739110
                    ----------
         time_total:  4.739201
    time_namelookup:  0.000855
       time_connect:  0.072247
    time_appconnect:  0.250336
   time_pretransfer:  0.250469
      time_redirect:  0.327261
 time_starttransfer:  4.681366
                    ----------
         time_total:  4.753394
    time_namelookup:  0.000467
       time_connect:  0.070945
    time_appconnect:  0.244066
   time_pretransfer:  0.244249
      time_redirect:  0.318052
 time_starttransfer:  4.757043
                    ----------
         time_total:  4.757153
xargs -P 0 -I {} ./curltime.sh -u   <<<   0.10s user 0.04s system 3% cpu 4.770 total

```

To work around this, we run a background process in our server which fetches fresh data on an 8-second interval.

When users call the `/incidents` endpoint of our server, they are served a cached version.

The cached version can be served in 200ms instead of 5 seconds

```
./curltime.sh http://localhost:9000/incidents
    time_namelookup:  0.000224
       time_connect:  0.000318
    time_appconnect:  0.000000
   time_pretransfer:  0.000348
      time_redirect:  0.000000
 time_starttransfer:  0.001407
                    ----------
         time_total:  0.001648
```

### Timing external API Python logic
There is a script called `query_api.py` which uses the same logic as the server
to download all incident data and identities from the API.

It runs with `debug=True` to show additional timings.

```
python query_api.py
Downloading identities
Fetching https://incident-api.use1stag.elevatesecurity.io/identities took 0:00:00.290214
Downloading incident_data
Fetching https://incident-api.use1stag.elevatesecurity.io/incidents/probing took 0:00:03.568728
Processing the incident data for probing took 0.017262042965739965
Fetching https://incident-api.use1stag.elevatesecurity.io/incidents/executable took 0:00:03.776800
Processing the incident data for executable took 0.017712001921609044
Fetching https://incident-api.use1stag.elevatesecurity.io/incidents/unauthorized took 0:00:03.959925
Fetching https://incident-api.use1stag.elevatesecurity.io/incidents/other took 0:00:03.968137
Fetching https://incident-api.use1stag.elevatesecurity.io/incidents/misuse took 0:00:04.009898
Fetching https://incident-api.use1stag.elevatesecurity.io/incidents/intrusion took 0:00:04.011085
Fetching https://incident-api.use1stag.elevatesecurity.io/incidents/denial took 0:00:03.978759
Processing the incident data for other took 0.017270259093493223
Processing the incident data for unauthorized took 0.013270154828205705
Processing the incident data for denial took 0.013277263846248388
Processing the incident data for misuse took 0.015176763059571385
Processing the incident data for intrusion took 0.013395512942224741
Completed fetching 2100 incidents with 0 errors
It took 5.0616135210730135 to fetch and process the data
```

