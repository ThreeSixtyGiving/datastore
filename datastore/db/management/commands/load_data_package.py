import copy

import db.models as db

from db.management.commands.load_datagetter_data import (
    Command as LoadDatagetterDataCommand,
)


class Command(LoadDatagetterDataCommand):
    help = (
        "Loads data that has been output by the datastore's create_data_package command"
    )
    """ Load a data package created by create_data_package.
    Note:
          * This performs no additional_data processing on the incoming data
          * This separates the data by treating it like a new GetterRun
    """

    def load_data(self):
        grants_added = 0
        dataset = self.load_dataset_data()

        getter_run = db.GetterRun.objects.create()

        for ob in dataset:
            prefix = ob["publisher"]["prefix"]
            publisher, c = db.Publisher.objects.get_or_create(
                getter_run=getter_run,
                prefix=prefix,
                data=ob["publisher"],
                org_id=ob["publisher"].get("org_id", "unknown"),
                name=ob["publisher"]["name"],
                source=db.Entity.PUBLISHER,
            )

            source_file = db.SourceFile.objects.create(data=ob, getter_run=getter_run)

            grant_data = self.load_grant_data(ob["datagetter_metadata"]["json"])

            grant_bulk_insert = []

            for grant in grant_data["grants"]:
                additional_data = copy.deepcopy(grant["additional_data"])
                del grant["additional_data"]

                grant_bulk_insert.append(
                    db.Grant(
                        grant_id=grant["id"],
                        source_file=source_file,
                        publisher=publisher,
                        data=grant,
                        additional_data=additional_data,
                        getter_run=getter_run,
                    )
                )

            db.Grant.objects.bulk_create(grant_bulk_insert)
            grants_added = grants_added + len(grant_data["grants"])

        return grants_added
