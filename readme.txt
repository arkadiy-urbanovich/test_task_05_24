To add some test data, run
> docker-compose up -d init_elastic
It downloads 800mb archive of wikipedia article summaries, so it takes a while.
If it breaks in the process, it's fine, it should have enough data for testing anyway

To start server, run
> docker-compose up -d web

To check the docs, please see http://localhost/docs (server must be running)
