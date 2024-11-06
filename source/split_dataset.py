from datasets import *


ds = load_dataset('KnotANumber/candle')

train_testvalid = ds['train'].train_test_split(test_size=0.2)
# Split the 10% test + valid in half test, half valid
# test_valid = train_testvalid['test'].train_test_split(test_size=0.5)
# gather everyone if you want to have a single DatasetDict
ds = DatasetDict({
    'train': train_testvalid['train'],
    'validation': train_testvalid['test']})

ds.push_to_hub('KnotANumber/candle')