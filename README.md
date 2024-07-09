## Setting up the Project for Development

```bash
pip install -r requirements/dev.txt
```

Create `.env` file. A sample file is provided along with the repository.
Update configuration in the `.env` file.

Run the migrations.

```bash
alembic upgrade heads
```

Run the project with

```bash
uvicorn core.gateway:app --reload
```