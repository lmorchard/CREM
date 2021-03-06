from app import app
from app import db
from app.models import Convention, Event, Track, Room, RoomGroup, Timeslot
from flask import jsonify, request
import json
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.exc import SQLAlchemyError
import datetime

def jsdate2py(s):
    """
    Converts a string to a Python datetime object. Returns None if the string
    cannot be converted. An example of the string is:

    2016-4-29T:20
    """
    try:
        parts = s.strip().split('T:')
        dateparts = parts[0].split('-')
        year = int(dateparts[0])
        month = int(dateparts[1])
        day = int(dateparts[2])
        hour = int(parts[1])
    except Exception:
        return None
    return datetime.datetime(year, month, day, hour, 0, 0)

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/admin')
def adminPage():
    return app.send_static_file('/views/admin.html')

@app.route('/convention.json', methods=['GET', 'POST'])
def convention():
    if request.method == 'GET':
        conventions = Convention.query.all()
        return jsonify(configs = [i.configs for i in conventions])
    else:
        content = request.json
        try:
            convention = Convention.query.one()
        except MultipleResultsFound:
            # Error: there should be one and only one convention record.
            return ('There is more than one convention record.', 500)
        convention.name = content['name']

        # Convert the start date to a Python datetime object.
        start_dt = jsdate2py(content['start_dt'])
        if start_dt is None:
            return ('Unable to parse the convention start date.', 500)
        convention.start_dt = start_dt

        # Convert the timeslot length from minutes to a timedelta object.
        convention.timeslot_length = datetime.timedelta(0, int(content['timeslot_length']) * 60)

        convention.number_of_timeslots = content['number_of_timeslots']

        # Update the database.
        try:
            db.session.add(convention)
            db.session.commit()
        except SQLAlchemyError, e:
            return ('Error updating the convention record: %s' % e, 500)
        return ('Convention data successfully updated.', 200)

@app.route('/number_of_timeslots.json')
def number_of_timeslots():
    number_of_timeslots = Timeslot.query.count()
    return jsonify(number_of_timeslots = number_of_timeslots)

@app.route('/tracks.json')
def tracks():
    tracklist = Track.query.all()
    return jsonify(tracknames = [i.names for i in tracklist])

@app.route('/columns.json')
def columns():
    return jsonify(
        columns = {
        'eventnumber': {'id':'eventnumber','name':'#',},
        'title': {'id':'title','name':'Title',},
        'track': {'id':'track','name':'Track',},
        'start': {'id':'start','name':'Start',},
        'duration': {'id':'duration','name':'Duration',},
        'room': {'id':'room','name':'Room',},
        'type': {'id':'type','name':'Type',},
        'presenters': {'id':'presenters','name':'Program Participants',},
        'resources': {'id':'resources','name':'Resources',},
        'description': {'id':'description','name':'Description',},
        'comments': {'id':'comments','name':'Staff Comments',},
        })

@app.route('/eventlist.json')
def events():
    eventlist = Event.query.all()
    return jsonify(eventlist = [i.useroutput for i in eventlist])

@app.route('/rooms.json', methods=['GET', 'POST'])
def rooms():
    if request.method == 'GET':
        roomlist = Room.query.all()
        return jsonify(rooms=[i.ui_rooms for i in roomlist])
    else:
        rooms = request.json
        for room in rooms:
            if 'id' not in room:
                db_room = Room()
            else:
                db_room = Room.query.get(room['id'])
            db_room.room_name = room['name']
            db_room.room_sq_ft = room['sq_ft']
            db_room.room_capacity = room['capacity']
            db_room.room_group_id = room['group_id']
            db.session.add(db_room)

        # Update the database.
        try:
            db.session.commit()
        except SQLAlchemyError, e:
            return ('Error updating the room records: %s' % e, 500)
        return ('Room configs successfully updated.', 200)

@app.route('/room_groups.json')
def room():
    roomgrouplist = RoomGroup.query.all()
    return jsonify(
        room_groups = [i.ui_room_groups for i in roomgrouplist],
        )

@app.route('/configs.json')
def combined_info():
    convention = Convention.query.first()
    tracks = Track.query.all()
    rooms = Room.query.all()
    room_groups = RoomGroup.query.all()
    return jsonify(
        {
            "convention": {
                "name": convention.name,
                "start_dt": convention.start_dt.strftime(convention.datetime_format),
                "timeslot_length": int(convention.timeslot_duration.total_seconds()/60),
                "number_of_timeslots": convention.number_of_timeslots,
            },
            "tracks": [i.names for i in tracks],
            "rooms": [{"name": i.room_name,
                       "capacity": i.room_capacity,
                       "sq_ft": i.room_sq_ft,
                       "group_id": i.room_group_id,
                       "id": i.id,
                       # TODO: rename this to bookings and make values returned useful.
                       "available_timeslots": [{"name": j.timeslot.name,
                                                "index": j.timeslot.timeslot_index
                                                }
                                               for j in i.bookings],
                       "suitable_events": [{"id": j.id,
                                            "title": j.title
                                            }
                                           for j in i.suitable_events]
                       }
                      for i in rooms],
            "room_groups": [i.ui_room_groups for i in room_groups]
        }
    )
