# Coleridge

Use Pydantic with RabbitMQ or to run background tasks.

## Example

```python
from time import sleep
from pydantic import BaseModel
from coleridge import Coleridge, Empty, Connection

class Poem(BaseModel):
    lines: List[str]


# Background task
coleridge = Coleridge()

@coleridge
def long_task(_: Empty) -> Poem:
    poem = Poem(lines=["In Xanadu did Kubla Khan",
            "A stately pleasure-dome decree:",])
    sleep(5)
    return poem

def print_poem(poem: Poem) -> None:
    for line in poem.lines:
        print(f"~~ {line} ~~")

def print_error(error: Exception) -> None:
    print(error)

# Assing a function to run when the exection finishes
long_task.on_finish = print_poem

# Or catch errors
long_task.on_error = print_error

# Run the task
long_task.run(Empty()) # It always requires a pydantic model, empty in this case


# Or use RabbitMQ instead of background functions
rabbit = Coleridge(Connection(host="localhost", port=5672))

@rabbit
def long_task_with_rabbit(poem: Poem) -> Empty:
    for line in poem.lines:
        print(f"~~ {line} ~~")
        sleep(5)
    return Empty()

long_task_with_rabbit.run(Poem(lines=["In Xanadu did Kubla Khan",
            "A stately pleasure-dome decree:",]))


```

You can also call the results directly like this:

```python
from time import sleep
from pydantic import BaseModel
from coleridge import Coleridge, Empty, Connection

class Poem(BaseModel):
    lines: List[str]


# Background task
coleridge = Coleridge()

@coleridge
def long_task(_: Empty) -> Poem:
    poem = Poem(lines=["In Xanadu did Kubla Khan",
            "A stately pleasure-dome decree:",])
    sleep(5)
    return poem

result = long_task.run(Empty())

while True:
    if result.finished:
        if result.success:
            print(result.result)
        elif result.error:
            print(result.error)
        break
```
