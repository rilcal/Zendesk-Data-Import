import pandas as pd
import zenpy
from zenpy.lib.api_objects import Ticket, User, Organization, OrganizationMembership, Comment
from zenpy.lib.exception import APIException


def create_ticket(zc, ticket_content, user_map, status_map):
    # Check if any users were not imported from the provided user data and create basic accound if not
    if ticket_content['submitter_id'] not in user_map:
        user_map = create_basic_user(zc, id=ticket_content['submitter_id'], usr_dict=user_map)
    if ticket_content['requester_id'] not in user_map:
        user_map = create_basic_user(zc, id=ticket_content['requester_id'], usr_dict=user_map)

    # Format list like strings in the data to proper python lists
    tags = ticket_content['tags'] \
        .replace("(", "") \
        .replace(")", "") \
        .replace("[", "") \
        .replace("]", "") \
        .replace("'", "")
    tags = tags.split(",")
    tags.append("RJC")

    # Create ticket object
    tik = Ticket(
        id=int(ticket_content['id']),
        created_at=ticket_content['created_at'],
        subject=ticket_content['subject'],
        status=status_map[ticket_content['status']],
        submitter_id=user_map[ticket_content['submitter_id']],
        requester_id=user_map[ticket_content['requester_id']],
        updated_at=ticket_content["updated_at"],
        due_at=ticket_content['due_at'],
        tags=tags,
        custom_fields={
            1500004511962: ticket_content['dept'],
            1500004439621: ticket_content['product information'],
            1500004511982: int(ticket_content['emp id']),
            1500004439641: ticket_content['start date'],
            1500004439661: ticket_content['subscription'],
            1500004439681: ticket_content['business name'],
            1500004512022: ticket_content['about']
        }
    )

    # Provided a generic assignee id if the data is not provided
    if ticket_content['assignee_id'] not in user_map:
        tik.assignee_id = "1507432183881"
    # look up the foreign assignee_id in the user map
    else:
        tik.assignee_id = user_map[ticket_content['assignee_id']]

    # Store the provided description as a comment object
    tik.comment = Comment(body=ticket_content['description'], public=False)

    # Create the ticket
    zc.tickets.create(tik)
    return user_map


def create_basic_user(zc, id, usr_map):
    # Create a simple user with only an id and name and email
    usr = User(id=id,
               email="usr_" + str(id) + "@example.com",
               name="usr_" + str(id),
               tags=['RJC'])
    created_user = zc.users.create(usr)

    # Save the new user in the user map
    usr_map[id] = created_user.id
    return usr_map


def create_user(zc, user_content, org_map, user_map):
    # Format the list like strings from the data into proper python lists
    tags = user_content['tags'] \
        .replace("(", "") \
        .replace(")", "") \
        .replace("[", "") \
        .replace("]", "") \
        .replace("'", "")
    tags = tags.split(",")
    tags.append("RJC")

    org_id = user_content['organization_id'] \
        .replace("(", "") \
        .replace(")", "") \
        .replace("[", "") \
        .replace("]", "") \
        .replace("'", "")
    org_id = org_id.split(",")
    org_id = list(map(int, org_id))

    # Set status variables
    email_already_present = False
    update = False

    # Loop through users in zendesk
    for user in zc.users():
        # if the provided email is in zendesk set the related status to true
        if user.email == user_content['email']:
            email_already_present = True
        # if the user is already in zendesk set the related status to true and save the zendesk id
        if user.email == user_content['email'] and user.name == user_content['name'] and user.organization_id == \
                org_map[org_id[0]]:
            update = True
            update_id = user.id

    # Define the user object from the given data to import into zendesk
    usr = User(name=user_content['name'],
               organization_id=org_map[org_id[0]],
               role=user_content['role'],
               notes=user_content['notes'],
               tags=tags,
               user_fields={
                   'group': user_content['group'].replace(" ", ""),
                   'subscription': user_content['api_subscription'],
                   'promotion_code': user_content['promotion_code'],
                   'employee_id': str(user_content['employee_id']),
                   'secondary_email': ""
               }
               )

    # if the user is already present in zendesk, update the user
    if update:
        # initialize invalid email count variable
        invalid_email_count = 0

        # Save the zendesk user id to the user object and store the provided email in the "secondary email" field
        usr.id = update_id
        usr.user_fields["secondary_email"] = user_content['email']

        while True:
            # Save the primary email for the user as an invalid email address
            usr.email = "invalid" + str(invalid_email_count) + "@example.com"

            # Attempt to create the user
            try:
                created_user = zc.users.update(usr)

            # if user creation error, try another invalid email
            except zenpy.lib.exception.APIException:
                invalid_email_count = invalid_email_count + 1

            # if any other error break from the loop
            else:
                break

    # if the email is already present create a user with an invalid email address
    elif email_already_present:
        invalid_email_count = 0
        usr.user_fields["secondary_email"] = user_content['email']
        while True:
            usr.email = "invalid" + str(invalid_email_count) + "@example.com"
            try:
                created_user = zc.users.create(usr)
            except zenpy.lib.exception.APIException:
                invalid_email_count = invalid_email_count + 1
            else:
                break

    # if the email is uniques and the user isn't in zendesk create the user
    else:
        usr.email = user_content['email']
        created_user = zc.users.create(usr)

    # Create organization members ships for the provided organization ties
    for org in org_id:
        o_id = org_map[org]
        create_organization_membership(zc, created_user.id, o_id)

    # update the user map with the new user
    new_user_map = user_map
    new_user_map[user_content['id']] = created_user.id
    return new_user_map


def create_organization(zc, org_content, org_map):
    # initialize status variable "update"
    update = False

    # Loops through the organizations in zendesk
    for organization in zc.organizations():
        # If the organization from the data is in zendesk then set the update status to true and store the zendesk org
        # id to the "update_id" variable
        if organization.name == org_content['name']:
            update = True
            update_id = organization.id

    # Format the list like strings from the data to proper python lists
    domain_names = org_content['domain_names'] \
        .replace("(", "") \
        .replace(")", "") \
        .replace("[", "") \
        .replace("]", "") \
        .replace("'", "") \
        .replace("_", "-")
    domain_names = domain_names.split(",")

    tags = org_content['tags'] \
        .replace("(", "") \
        .replace(")", "") \
        .replace("[", "") \
        .replace("]", "") \
        .replace("'", "") \
        .replace("_", "-")
    tags = tags.split(",")
    tags.append("RJC")

    # Define an organization object with the given data import into zendesk
    org = Organization(id=org_content['id'],
                       name=org_content["name"],
                       domain_names=domain_names,
                       details=org_content['details'],
                       notes=org_content['notes'],
                       organization_fields={"merchant_id": org_content['merchant_id']},
                       tags=tags)

    # If the organization name is already present then update the object in zendesk
    if update:
        org.id = update_id
        created_org = zc.organizations.update(org)
    # If the organization isn't present, create the organization in zendesk
    else:
        created_org = zc.organizations.create(org)

    # Staore the created or updated organization id's into the org map to establish a connection between the data and
    # zendesk
    new_org_map = org_map
    new_org_map[org_content['id']] = created_org.id

    return  new_org_map


def create_organization_membership(zc, user_id, org_id):

    # Defines an organizations membership object between a user and an org
    org_mem = OrganizationMembership(user_id=user_id, organization_id=org_id)

    # Attempts to import the organization membership into zendesk. If error, the user is already a member of that org
    try:
        zc.organization_memberships.create(org_mem)
    except APIException:
        print('User already a member of that organization')
    return


def get_tickets_data():
    # Retrieves the ticket data from the data folder
    tickets = pd.read_csv('data/tickets.csv')
    return tickets


def get_users_data():
    # Retrieves the user data from the data folder
    tickets = pd.read_csv('data/users.csv')
    return tickets


def get_organization_data():
    # Retrieves the organization data from the data folder
    tickets = pd.read_csv('data/organizations.csv')
    return tickets


def delete_all_users(zc):
    ### A function for removing all the users while testing the import process ###

    # Loop through all users and delete them except for William's and Riley's accounts
    for user in zc.users():
        if not user.email == "wtsang+pfd1@zendesk.com" and not user.email == "rileycallaghan96@gmail.com" and not user.name == "William Tsang":
            zc.users.delete(user)

    # Check if all users were deleted. If not repeat the delete process
    count = 0
    for usr in zc.users():
        count = count + 1
        if count > 3:
            delete_all_users(zc)


def delete_all_tickets(zc):
    ### A function for removing all the users while testing the import process ###

    # Loop through all the tickets and permanently delete the tickets
    for ticket in zc.tickets():
        zc.tickets.delete(ticket)
        zc.tickets.permanently_delete(ticket)

    # Check if all tickets where deleted. If not repeat the delete process
    count = 0
    for ticket in zc.tickets():
        count = count + 1
        if count > 0:
            delete_all_tickets(zc)
