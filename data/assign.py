import pandas as pd
import re
from datetime import datetime
import os 

def solve_choir_assignment(csv_file_path):
    """
    Solves the choir assignment problem based on availability and fairness.

    Constraints:
    1. Max 3 people per part (Soprano, Alto, Tenor, Bass) per slot.
    """

    NAME_COL = 'Name and Part'
    PART_COL = 'part'
    AVAIL_COL = 'Please select dates and times you are available on:'
    CHOIR_PARTS = ['Soprano', 'Alto', 'Tenor', 'Bass']
    OUTPUT_FILE = 'choir_assignment.csv'
    
    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
        return
    except Exception as e:
        print(f"An error occurred while loading the file: {e}")
        return

    # preprocess
    print("Processing availabilities...")
    
    # Select only the columns we need
    try:
        core_df = df[[NAME_COL, PART_COL, AVAIL_COL]].copy()
    except KeyError:
        print("Error: One of the required columns was not found.")
        print(f"Needed: '{NAME_COL}', '{PART_COL}', '{AVAIL_COL}'")
        print(f"Found: {df.columns.tolist()}")
        return

    # Clean data
    core_df[NAME_COL] = core_df[NAME_COL].str.strip()
    core_df[PART_COL] = core_df[PART_COL].str.strip()
    core_df = core_df.dropna(subset=[AVAIL_COL])
    core_df[AVAIL_COL] = core_df[AVAIL_COL].str.split(',')
    avail_df = core_df.explode(AVAIL_COL)
    avail_df[AVAIL_COL] = avail_df[AVAIL_COL].str.strip()
    avail_df = avail_df.rename(columns={AVAIL_COL: 'Slot'})
    avail_df = avail_df[avail_df['Slot'] != '']
    

    # Initialise
    all_people = avail_df[NAME_COL].unique()
    assignment_counts = pd.Series(0, index=all_people, dtype=int)
    all_slots = avail_df['Slot'].unique()
    
    # Helper function to parse custom date strings 
    def parse_slot_to_datetime(slot_str):
        # Assumes format like "Weds 19th Nov 11am"
        # For 2025
        try:
            no_day = slot_str.split(' ', 1)[-1]
            no_ordinal = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', no_day)
            parts = no_ordinal.split(' ') # e.g., ["19", "Nov", "11am"]
            if len(parts) != 3:
                # Handle unexpected format
                print(f"Warning: Could not parse date '{slot_str}'. Placing at end.")
                return datetime.max
    
            date_str_with_year = f"{parts[0]} {parts[1]} 2025 {parts[2]}"
            
            return datetime.strptime(date_str_with_year, "%d %b %Y %I%p")
        
        except Exception as e:
            print(f"Warning: Could not parse date '{slot_str}'. Placing at end. Error: {e}")
            # Put any unparseable dates at the end of the sort
            return datetime.max
    
    # Sort the unique slots using the helper function as the key
    all_slots_sorted = sorted(all_slots, key=parse_slot_to_datetime)
    
    # Create the final DataFrame with Slots as rows (now sorted)
    final_assignment_df = pd.DataFrame(
        index=all_slots_sorted,
        columns=CHOIR_PARTS
    )
    
    final_assignment_df.index.name = 'Slot'
    
    # Contraints

    # Loop through each slot in chronological order
    for slot in all_slots_sorted:
        for part in CHOIR_PARTS:
            
            # get all available candidates 
            candidates_df = avail_df[
                (avail_df['Slot'] == slot) & (avail_df[PART_COL] == part)
            ]
            
            candidates_names = candidates_df[NAME_COL]
            
            # If no one is available, just continue
            if len(candidates_names) == 0:
                continue
            
            # If 3 or fewer are available, they all get the slot
            if len(candidates_names) <= 3:
                assigned_names = candidates_names.tolist()
            
            # If MORE than 3 are available
            else:
                # Get current assignment count
                candidate_counts = assignment_counts.loc[candidates_names]
                candidates_sorted_by_count = candidate_counts.sort_values(ascending=True)
                
                # Take the top 3 
                assigned_names = candidates_sorted_by_count.head(3).index.tolist()

            final_assignment_df.at[slot, part] = '\n'.join(assigned_names)
            assignment_counts.loc[assigned_names] += 1

    # display
    final_assignment_df = final_assignment_df.fillna("")
    final_assignment_df.to_csv(OUTPUT_FILE)
    
    print("\n--- Success! ---")
    print(f"Choir assignment complete. File saved as '{OUTPUT_FILE}'")
    
    print("\nPreview of the Assignment DataFrame:")
    print(final_assignment_df.head())
    
    return final_assignment_df

def generate_and_save_summary_stats():
    """
    Generates summary statistics from the final choir assignment,
    groups them by voice part, and saves to a new CSV.
    """
    ASSIGNMENT_FILE = 'choir_assignment.csv'
    RAW_DATA_FILE = os.path.join(os.getcwd(), 'data', 'responses.csv')
    OUTPUT_FILE = 'assignment_summary_stats_by_part.csv'
    
    NAME_COL = 'Name and Part'
    PART_COL = 'part'
    AVAIL_COL = 'Please select dates and times you are available on:'
    
    # load
    try:
        assignment_df = pd.read_csv(ASSIGNMENT_FILE, index_col=0)
    except FileNotFoundError:
        print(f"Error: The file '{ASSIGNMENT_FILE}' was not found.")
        print("Please run the 'solve_choir_assignment.py' script first.")
        return
    except Exception as e:
        print(f"An error occurred loading '{ASSIGNMENT_FILE}': {e}")
        return

    try:
        raw_df = pd.read_csv(RAW_DATA_FILE)
    except FileNotFoundError:
        print(f"Error: The file '{RAW_DATA_FILE}' was not found.")
        return
    except Exception as e:
        print(f"An error occurred loading '{RAW_DATA_FILE}': {e}")
        return
        
    print("Successfully loaded input files.")

    # get assignment counts
    stacked_series = assignment_df.stack()
    non_empty_series = stacked_series[stacked_series != ""]
    list_of_names_series = non_empty_series.str.split('\n')
    exploded_names = list_of_names_series.explode()
    name_counts_series = exploded_names.value_counts()
    stats_df = name_counts_series.reset_index()
    stats_df.columns = ['Name', 'TotalAssignedSlots']
    
    # name part mapping
    # Check
    if not {NAME_COL, PART_COL, AVAIL_COL}.issubset(raw_df.columns):
        print(f"Error: Raw data file is missing required columns.")
        print(f"Needed: '{NAME_COL}', '{PART_COL}', and '{AVAIL_COL}'")
        return
        
    mapping_df = raw_df[[NAME_COL, PART_COL, AVAIL_COL]].copy()
    mapping_df[NAME_COL] = mapping_df[NAME_COL].str.strip()
    mapping_df[PART_COL] = mapping_df[PART_COL].str.strip()
    
    # Total wanted, one entry pp
    mapping_df[AVAIL_COL] = mapping_df[AVAIL_COL].fillna('')
    mapping_df['TotalWantedSlots'] = mapping_df[AVAIL_COL].apply(
        lambda x: 0 if x == '' else len(x.split(','))
    )
    mapping_df = mapping_df.drop_duplicates(subset=[NAME_COL])
    
    # merge, sort , save
    merged_df = pd.merge(
        stats_df,
        mapping_df,
        left_on='Name',
        right_on=NAME_COL,
        how='left'
    )
    merged_df[PART_COL] = merged_df[PART_COL].fillna('Unknown')
    final_df = merged_df[[PART_COL, 'Name', 'TotalAssignedSlots', 'TotalWantedSlots']]
    final_df = final_df.sort_values(
        by=[PART_COL, 'TotalAssignedSlots', 'Name'],
        ascending=[True, False, True]
    )
    final_df.to_csv(OUTPUT_FILE, index=False)
    
    print("\n--- Success! ---")
    print(f"Summary statistics grouped by part saved as '{OUTPUT_FILE}'")
    
    print("\nPreview of Statistics:")
    print(final_df.head())


if __name__ == "__main__":
    # Use the file you uploaded
    assignment_df = solve_choir_assignment("data/responses.csv")
    
    # Generate stats *after* the assignment is complete
    if assignment_df is not None:
        generate_and_save_summary_stats()