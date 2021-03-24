# ARCHIVED -- FUNCTIONALITY ROLLED INTO BASE MERMAID API

# mermaid-summary-api
##Unauthenticated read-only aggregated MERMAID data API
## Setup notes
- Must have api_db Docker container and mermaid-api network running before setting up local mermaid-summary-api 
environment (i.e., run fab fresh_install in mermaid-api first, then run fresh_install here).
- Note zappa requires a virtual environment, so shell commands need to activate it before running python. See fabfile.
- Note this project is a second Django instance accessing the same database as mermaid-api but with different 
versions of Python and Django (and libraries). Until we upgrade mermaid-api (and even afterward), avoid doing aything
 that touches the database. For example, if you have to create a migration, use `...migrate summary_api` (with `app 
 label`).
 - A .env file is required in the root, with these vars defined:
 AWS_ACCESS_KEY_ID=  
 AWS_SECRET_ACCESS_KEY=  
 AWS_DEFAULT_REGION=  
 DB_NAME=  
 DB_USER=  
 PGPASSWORD=  
 DB_PASSWORD=  
 DB_HOST=  
 DB_PORT=  
 ENV=local  
 SECRET_KEY=  
- Zappa operations: https://github.com/Miserlou/Zappa  
`fab shell` and then (e.g.):  
`zappa update dev`  
`zappa update prod`  
`zappa manage dev "migrate summary_api"`  
Use  local zapp environment to run collectstatic, i.e. `python manage.py collectstatic --noinput`  (`zappa manage dev
 "collectstatic --noinput"` timing out currently)  
For zappa deployment operations to work, the appropriate settings must be set in `/src/zappa_settings.json`. See the 
template in that directory, [zappa documentation](https://github.com/Miserlou/Zappa), and [this helpful django-zappa 
guide](https://romandc.com/zappa-django-guide/) for details. 
