import pandas as pd
import numpy as np

def get_value_counts_matrix(df):
    """
    Creates a matrix of value counts for each column in the input DataFrame.
    Each row represents a column from the original DataFrame, containing the sorted counts of unique values.
    Rows are padded with zeros to match the length of the column with the most unique values.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame to analyze
        
    Returns:
    --------
    pandas.DataFrame
        A DataFrame where each row contains the sorted value counts for a column from the input DataFrame,
        padded with zeros if necessary.
    """
    # Get value counts for each column using numpy's unique with counts
    value_counts = {}
    for col in df.columns:
        # Convert column to numpy array and get unique values and counts
        col_array = df[col].to_numpy()
        _, counts = np.unique(col_array, return_counts=True)
        # Sort counts in descending order
        counts = np.sort(counts)[::-1]
        value_counts[col] = counts
    
    # Find the maximum number of unique values across all columns
    max_unique = max(len(counts) for counts in value_counts.values())
    
    # Pad each count array with zeros to match the maximum length
    padded_counts = {col: np.pad(counts, (0, max_unique - len(counts)), 
                                mode='constant', constant_values=0)
                    for col, counts in value_counts.items()}
    
    # Create the output DataFrame
    result_df = pd.DataFrame.from_dict(padded_counts, orient='index')
    
    return result_df 