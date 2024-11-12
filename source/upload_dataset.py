from datasets import load_dataset, DatasetDict

def create_and_push_image_dataset(directory_path, repo_id, split_ratio=0.2):
    # Load dataset directly from the image directory
    dataset = load_dataset("imagefolder", data_dir=directory_path)

    # Split dataset into train and validation sets
    split_dataset = dataset["train"].train_test_split(test_size=split_ratio, stratify_by_column="label")
    dataset_dict = DatasetDict({"train": split_dataset["train"], "validation": split_dataset["test"]})

    # Push to Hugging Face Hub
    dataset_dict.push_to_hub(repo_id)

# Usage example
create_and_push_image_dataset("./data/compiled/candle", "KnotANumber/candle")