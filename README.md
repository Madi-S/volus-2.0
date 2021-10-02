### To init database:

1. Create sqlite directory in the root directory
2. Create volus.db in this new sqlite directory
3. Open terminal in the root directory
4. `python`
5.

```python
from models import *
db.drop_all()
db.create_all()
```

### To run:

1. Optionally run filler.py to fill the website with sample data
2. `python run.py`
