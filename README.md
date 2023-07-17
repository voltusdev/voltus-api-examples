# Voltus API Examples

Examples of using the [Voltus API].
These examples are written in Python using [Flask] and [requests] (two popular libraries for writing web servers and making HTTP requests, respectively).

> **Note**
> These examples are deliberately simplified to be readable and understandable by a broad audience.
> They are intended to help developers learn how to use the Voltus API and should not be considered "production ready".

To run these examples, we recommend using [virtualenv], which allows you to install
the above libraries without affecting the rest of your system.

On Windows:

```
python3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On Linux or MacOS:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

After that, you should be able to run the examples. For example:

```
cd polling
python dispatch-polling-stage2.py
```

[Voltus API]: https://api.voltus.co/docs/
[Flask]: https://github.com/pallets/flask
[requests]: https://requests.readthedocs.io/en/latest/
[virtualenv]: https://docs.python.org/3/library/venv.html
