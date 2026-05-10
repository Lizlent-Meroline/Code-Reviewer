# Libraries Documentation

A reference guide for all libraries and modules used in this project.

---

## 1. `os`
Built-in Python module for interacting with the operating system.

| Function | Description |
|----------|-------------|
| `os.path.exists(path)` | Returns `True` if the path exists on disk |
| `os.path.join(*paths)` | Joins path components into a single path |
| `os.path.isfile(path)` | Returns `True` if the path is a file |
| `os.makedirs(path, exist_ok=True)` | Creates directories recursively |
| `os.remove(path)` | Deletes a file |
| `os.getenv(key, default)` | Reads an environment variable |
| `os.cpu_count()` | Returns the number of CPU cores |
| `os.stat(path)` | Returns file metadata (size, mtime, etc.) |
| `os.path.getsize(path)` | Returns file size in bytes |
| `os.path.splitext(path)` | Splits filename into name and extension |
| `os.walk(top)` | Recursively walks a directory tree |

---

## 2. `shutil`
Built-in module for high-level file and directory operations.

| Function | Description |
|----------|-------------|
| `shutil.rmtree(path)` | Recursively deletes a directory and all its contents |
| `shutil.copy(src, dst)` | Copies a file from source to destination |
| `shutil.copytree(src, dst)` | Recursively copies an entire directory tree |
| `shutil.move(src, dst)` | Moves a file or directory to a new location |
| `shutil.disk_usage(path)` | Returns disk usage statistics (total, used, free) |
| `shutil.make_archive(base, format, root_dir)` | Creates a compressed archive (zip, tar, etc.) |

---

## 3. `requests`
Third-party library for making HTTP requests.

| Function | Description |
|----------|-------------|
| `requests.get(url, params, headers)` | Sends a GET request |
| `requests.post(url, json, headers)` | Sends a POST request with a JSON body |
| `requests.put(url, data, headers)` | Sends a PUT request |
| `requests.delete(url, headers)` | Sends a DELETE request |
| `response.json()` | Parses the response body as JSON |
| `response.status_code` | HTTP status code of the response (e.g. 200, 404) |
| `response.text` | Raw response body as a string |
| `response.raise_for_status()` | Raises an exception if the status code indicates an error |
| `requests.Session()` | Creates a session to reuse connections and headers |

---

## 4. `git` (GitPython)
Third-party library for interacting with Git repositories programmatically.

| Function / Class | Description |
|------------------|-------------|
| `git.Repo(path)` | Opens an existing Git repository |
| `git.Git(path).clone(url, name, *flags)` | Clones a remote repository with optional flags |
| `repo.remotes.origin.refs` | Accesses remote branch references |
| `repo.git.checkout(branch)` | Checks out a branch or tag |
| `repo.git.fetch(*args)` | Fetches from the remote |
| `repo.tags` | Lists all tags in the repository |
| `repo.iter_commits(branch, max_count)` | Iterates over commits on a branch |
| `commit.hexsha` | The full SHA hash of a commit |
| `commit.message` | The commit message string |
| `commit.author.name` | Name of the commit author |
| `commit.committed_datetime` | Datetime the commit was made |
| `git.GitCommandError` | Exception raised when a Git command fails |

---

## 5. `re`
Built-in module for regular expressions.

| Function | Description |
|----------|-------------|
| `re.compile(pattern)` | Compiles a regex pattern into a reusable object |
| `re.match(pattern, string)` | Matches pattern at the start of a string |
| `re.search(pattern, string)` | Searches anywhere in the string for a match |
| `re.findall(pattern, string)` | Returns a list of all non-overlapping matches |
| `re.finditer(pattern, string)` | Returns an iterator of match objects |
| `re.sub(pattern, repl, string)` | Replaces matches with a replacement string |
| `re.split(pattern, string)` | Splits a string by the pattern |
| `pattern.match(string)` | Matches using a pre-compiled pattern |
| `match.group()` | Returns the matched string |

---

## 6. `typing` — `List`, `Dict`, `Optional`
Built-in module providing type hint support.

| Type | Description |
|------|-------------|
| `List[T]` | A list containing elements of type `T` (e.g. `List[str]`) |
| `Dict[K, V]` | A dictionary with key type `K` and value type `V` |
| `Optional[T]` | A value that is either type `T` or `None` |
| `Tuple[T, ...]` | A tuple with typed elements |
| `Union[T1, T2]` | A value that can be one of several types |
| `Any` | Disables type checking for a value |
| `Callable[[args], return]` | Represents a callable (function) with typed signature |

> **Note:** In Python 3.9+, you can use `list[str]`, `dict[str, int]`, and `str | None` directly without importing from `typing`.

---

## 7. `ast`
Built-in module for parsing and analyzing Python source code as an Abstract Syntax Tree.

| Function / Class | Description |
|------------------|-------------|
| `ast.parse(source)` | Parses Python source code into an AST |
| `ast.iter_child_nodes(node)` | Yields direct child nodes of an AST node |
| `ast.walk(node)` | Recursively yields all nodes in the tree |
| `ast.FunctionDef` | AST node representing a `def` function |
| `ast.AsyncFunctionDef` | AST node representing an `async def` function |
| `ast.ClassDef` | AST node representing a `class` definition |
| `ast.Return` | AST node representing a `return` statement |
| `ast.Raise` | AST node representing a `raise` statement |
| `ast.ExceptHandler` | AST node representing an `except` clause |
| `node.lineno` | Line number where the node appears in source |
| `node.name` | Name attribute of function/class nodes |
| `isinstance(node, ast.NodeType)` | Checks if a node is of a specific AST type |

---

## 8. `json`
Built-in module for encoding and decoding JSON data.

| Function | Description |
|----------|-------------|
| `json.loads(string)` | Parses a JSON string into a Python object |
| `json.dumps(obj)` | Serializes a Python object to a JSON string |
| `json.dump(obj, file)` | Writes a Python object as JSON to a file |
| `json.load(file)` | Reads and parses JSON from a file object |
| `json.dumps(obj, indent=2)` | Pretty-prints JSON with indentation |
| `json.dumps(obj, ensure_ascii=False)` | Preserves non-ASCII characters in output |

---

## 9. `uuid`
Built-in module for generating universally unique identifiers.

| Function | Description |
|----------|-------------|
| `uuid.uuid4()` | Generates a random UUID (version 4) |
| `str(uuid.uuid4())` | Converts UUID to a string like `"550e8400-e29b-41d4-a716-446655440000"` |
| `uuid.uuid1()` | Generates a UUID based on host and current time |
| `uuid.UUID(string)` | Parses a UUID from a string |

---

## 10. `datetime`
Built-in module for working with dates and times.

| Function / Class | Description |
|------------------|-------------|
| `datetime.datetime.now()` | Returns the current local date and time |
| `datetime.datetime.utcnow()` | Returns the current UTC date and time |
| `datetime.datetime.now(timezone.utc)` | Returns timezone-aware current UTC time |
| `datetime.isoformat()` | Formats a datetime as an ISO 8601 string |
| `datetime.datetime.fromisoformat(s)` | Parses an ISO 8601 string into a datetime |
| `datetime.timedelta(days, hours, seconds)` | Represents a duration or difference between times |
| `datetime.timezone.utc` | The UTC timezone constant |
| `datetime + timedelta` | Adds a duration to a datetime |

---

## 11. `asyncio`
Built-in module for writing asynchronous, concurrent code using `async`/`await`.

| Function | Description |
|----------|-------------|
| `asyncio.run(coroutine)` | Runs a top-level async function |
| `await asyncio.sleep(seconds)` | Pauses execution for a given duration without blocking |
| `await asyncio.to_thread(fn, *args)` | Runs a blocking function in a thread pool |
| `asyncio.get_event_loop()` | Returns the current event loop |
| `asyncio.run_coroutine_threadsafe(coro, loop)` | Schedules a coroutine from a non-async thread |
| `asyncio.gather(*coroutines)` | Runs multiple coroutines concurrently |
| `asyncio.create_task(coroutine)` | Schedules a coroutine as a background task |
| `asyncio.Queue()` | An async-safe queue for producer/consumer patterns |

---

## 12. `sqlite3`
Built-in module for working with SQLite databases.

| Function / Method | Description |
|-------------------|-------------|
| `sqlite3.connect(path)` | Opens (or creates) a SQLite database file |
| `con.execute(sql, params)` | Executes a SQL statement with optional parameters |
| `con.executemany(sql, seq)` | Executes a SQL statement for each item in a sequence |
| `con.commit()` | Commits the current transaction |
| `con.close()` | Closes the database connection |
| `con.row_factory = sqlite3.Row` | Makes rows accessible by column name |
| `cursor.fetchone()` | Returns the next row from a query result |
| `cursor.fetchall()` | Returns all rows from a query result |
| `cursor.rowcount` | Number of rows affected by the last statement |
| `con.execute("PRAGMA foreign_keys = ON")` | Enables foreign key constraint enforcement |

---

## 13. `concurrent.futures` — `ThreadPoolExecutor`
Built-in module for running tasks concurrently using threads or processes.

| Function / Method | Description |
|-------------------|-------------|
| `ThreadPoolExecutor(max_workers)` | Creates a pool of worker threads |
| `executor.submit(fn, *args)` | Submits a callable to run in a thread, returns a `Future` |
| `executor.map(fn, iterable)` | Maps a function over an iterable using threads |
| `executor.shutdown(wait=True)` | Shuts down the executor, optionally waiting for completion |
| `as_completed(futures)` | Yields futures as they complete (not in submission order) |
| `future.result()` | Blocks and returns the result of the future |
| `future.done()` | Returns `True` if the future has finished |
| `future.exception()` | Returns the exception raised by the future, if any |

---

## 14. `fastapi` — `HTTPException`
Part of the FastAPI framework for raising HTTP error responses.

| Usage | Description |
|-------|-------------|
| `HTTPException(status_code, detail)` | Raises an HTTP error response with a status code and message |
| `status_code=400` | Bad Request — invalid input from the client |
| `status_code=401` | Unauthorized — authentication required |
| `status_code=403` | Forbidden — authenticated but not allowed |
| `status_code=404` | Not Found — resource does not exist |
| `status_code=422` | Unprocessable Entity — validation error |
| `status_code=500` | Internal Server Error — unexpected server failure |
| `raise HTTPException(404, detail="Not found")` | Typical usage inside a route handler |

---

## 15. `pydantic` — `BaseModel`
Data validation and settings management library used heavily with FastAPI.

| Feature | Description |
|---------|-------------|
| `class MyModel(BaseModel)` | Defines a data model with typed fields |
| `model = MyModel(**data)` | Creates an instance, validating input automatically |
| `model.field` | Accesses a validated field value |
| `model.dict()` | Converts the model to a plain Python dictionary |
| `model.json()` | Serializes the model to a JSON string |
| `Optional[str] = None` | Marks a field as optional with a default of `None` |
| `Field(default, description)` | Adds metadata or constraints to a field |
| Automatic validation | Raises `ValidationError` if input types don't match |
| Used in FastAPI routes | Request bodies are automatically parsed and validated |

---
