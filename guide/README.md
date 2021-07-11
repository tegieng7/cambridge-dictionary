# Prepare data

### Crawl and parse data from Cambridge online

```bash
python cambridge crawl english-vietnamese
python cambridge parse english-vietnamese
python cambridge collect english-vietnamese
python cambridge generate english-vietnamese
```

### Debug

```bash
python cambridge debug english-vietnamese --option sample
python cambridge debug english-vietnamese --option layout
python cambridge debug english-vietnamese --option export
python cambridge debug english-vietnamese --option wordname
```

# Variables

```bash
export MGPASSWD="password"
export MGURI="mongodb://root:${MGPASSWD}@localhost:27017"
export MGDBNAME="cambridge"
```

# Setup Mongo database

Check config

```bash
docker-compose -f mongodb.yaml config
```

Setup Mongo database

```bash
docker-compose -f mongodb.yaml up -d
```

# Documents

[Creating Dictionaries](https://kdp.amazon.com/en_US/help/topic/G2HXJS944GL88DNV)

[Guidelines for Converting XMDF to KF8](https://kdp.amazon.com/en_US/help/topic/GRWTKMGXU2MV5KKP#kindlegen)