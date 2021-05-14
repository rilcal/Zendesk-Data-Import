import os
from dotenv import load_dotenv
import zenpy
from zendeskFunctions import create_user,create_organization,\
    create_ticket, get_users_data, get_organization_data, get_tickets_data
import pickle


def main():
    # Get all env variables from the .env document
    load_dotenv()
    domain = os.getenv("DOMAIN")
    ak = os.getenv("API_KEY")
    un = os.getenv("USERNAME")

    # Format environment variable into the creds object for Zenpy module
    creds = {
        'email': un,
        'token': ak,
        'subdomain': domain
    }

    # Create Zenpy client (with credentials) to interact with the web API
    zenpy_client = zenpy.Zenpy(**creds)

    # Get all provided data
    all_tickets = get_tickets_data()
    all_organizations = get_organization_data()
    all_users = get_users_data()

    # Clean data by replacing NaN values with ""
    all_tickets.fillna("", inplace=True)
    all_users.fillna("", inplace=True)
    all_organizations.fillna("", inplace=True)

    # Initialize an organization map to map between given organization id's and the zendesk generated organization id's
    org_map = {}

    # Loop through the organization and create zendesk objects while updating the organization map
    for i in range(0, len(all_organizations)):
        new_org_map = create_organization(zenpy_client, all_organizations.loc[i], org_map)
        org_map = new_org_map

    # Optionally save the organization map to a pickle object in the current folder
    with open('pickles/org_mapping.pkl', 'wb') as handle:
        pickle.dump(org_map, handle)

    # Optionally load the organizaiton map from a pickle object
    with open('pickles/org_mapping.pkl', 'rb') as handle:
        org_map = pickle.load(handle)

    # Initialize a user map to map between given data user id's and the zendesk generated user id's
    user_map = {}

    # Loop through the user data and create zendesk objects while updating the user map
    for i in range(0, len(all_users)):
        new_usr_map = create_user(zenpy_client, all_users.loc[i], org_map, user_map)
        user_map = new_usr_map

    # Optionally save the user map to a pickle object in the current folder
    with open('pickles/user_mapping.pkl', 'wb') as handle:
        pickle.dump(user_map, handle)

    # Optionally load the user map from a pickle object
    with open('pickles/user_mapping.pkl', 'rb') as handle:
        user_map = pickle.load(handle)

    # Define the status map which defines the mapping between the legacy statuses and zendesk statuses
    status_map = {
        "open": "open",
        "assigned": "open",
        "waiting": "pending",
        "external": "hold",
        "engineering": "hold",
        "resolved": "solved",
        "done": "closed",
        "retracted": "closed",
        "new": "new"
    }

    # Loop through the ticket data and import the tickets into the Zendesk enviornment
    for i in range(0, len(all_tickets)):
        user_mapping = create_ticket(zenpy_client, all_tickets.loc[i], user_map, status_map)
        user_dict = user_mapping

    # Save the user data with any new users created from the ticket process to a pickle object
    with open('pickles/user_mapping.pkl', 'wb') as handle:
        pickle.dump(user_dict, handle)


if __name__ == "__main__":
    main()
