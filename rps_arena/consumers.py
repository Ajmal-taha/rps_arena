import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import GameRoom, GamePlayer
import redis

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

class GameConsumer(AsyncWebsocketConsumer):
# Connect part
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"game_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"User connected: {self.scope['user'].id} in room: {self.room_name}")

        game_room = await sync_to_async(GameRoom.objects.get)(room_name=self.room_name)
        usernames = await sync_to_async(list)(
            game_room.users.values_list("username", flat=True)
        )

        # initializing round number by caching it
        round_number_key = f"rounds:{self.room_name}:" # Redis key for round number
        redis_client.set(round_number_key, 1)

        print("inside connect")
        if len(usernames) == 2:
            # broadcast game_start message
            await self.broadcast_game_start(usernames)

    # broadcasting game start message to whole group(group send)
    async def broadcast_game_start(self, usernames):
        print('inside broadcast_game_start')
        # clearing any play again cache set before
        play_again_key_pattern = f"play_again:{self.room_name}"
        redis_client.delete(play_again_key_pattern)
        # broadcasting game start message to all groups
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "self_send_game_start",
                "users": usernames
            }
        )

    async def self_send_game_start(self, event):
        users = event['users']
        you = self.scope['user'].username
        if users[0] == you:
            opponent = users[1]
        else:
            opponent = users[0]
        
        # sending game start message to frontend
        await self.send(text_data = json.dumps({
            "type": "game_start",
            "you": you,
            "opponent": opponent,
        }))

# Receive part
    async def receive(self, text_data):
        print('inside receive')
        content = json.loads(text_data)
        message_type = content.get("type")
        print(f"received message: {content}")

        message_handlers = {
            "my_choice": self.my_choice,
            "leave": self.leave,
            "play_again": self.play_again,
        }

        print(f'handler used: {message_type}')
        handler = message_handlers.get(message_type)

        if handler:
            await handler(content)
        else:
            print(f"Unhandled message type: {message_type}")

    #handling my_choice
    async def my_choice(self, content):
        content = content.get('content')
        player_choice = content.get('choice')
        player = self.scope['user'].username
        print(f"In my_choice: {content}")

        #storing player's choices in Redis(caching)
        room_key = f"game:{self.room_name}"  # Redis key for the room
        player_key = f"{room_key}:{player}"  # Redis key for the player

        # Check if the player's choice is already stored
        existing_choice = redis_client.get(player_key)
        if not existing_choice:
            redis_client.set(player_key, player_choice)
            print(f"Stored in Redis: {player_key} -> {player_choice}")

        # Fetch all player choices from Redis
        room_keys = redis_client.keys(f"{room_key}:*")
        #creating a player(username):choice dict called player_choices
        player_choices = {
            key.split(":")[-1]: redis_client.get(key) for key in room_keys
        }
        print(f"Player choices in Redis: {player_choices}")

        # Calculate result if both players have made a choice
        if len(player_choices) == 2:
            # getting result if both players made choice
            result = await self.round_decide(player_choices)
            print(f'Result of game: {result}')

            # adding points to player won in Redis cache
            if result.get('result_status') == 'not_draw':
                player = result.get('winner')
                room_key = f"game:{self.room_name}"  # Redis key for the room
                player_point_key = f"points:{self.room_name}:{player}" # Redis key for player's points

                # Check if the player's point is already exist in cache
                existing_points = redis_client.get(player_point_key)
                if not existing_points:
                    redis_client.set(player_point_key, 1)
                    print(f"Stored in Redis: {player_point_key} -> {1}")
                else:
                    # Convert existing points to integer(stored in binary), increment it, and update in Redis
                    new_points = int(existing_points) + 1
                    redis_client.set(player_point_key, new_points)
                    print(f"Updated in Redis: {player_point_key} -> {new_points}")

            # broadcasting message to whole group about result
            await self.broadcast_round_result_message(result)

            # Clear the cache for this round after the result is calculated
            await self.clear_cache_round()

    async def round_decide(self, player_choices):
        # calculating round result
        players = list(player_choices.keys())
        choices = list(player_choices.values())

        if choices[0] == choices[1]:
            return {"result_status": "draw", "choices": player_choices}
        elif (choices[0] == "rock" and choices[1] == "scissors") or \
             (choices[0] == "scissors" and choices[1] == "paper") or \
             (choices[0] == "paper" and choices[1] == "rock"):
            winner = players[0]
        else:
            winner = players[1]

        return {"result_status": "not_draw", "winner": winner, "choices": player_choices}
    
    # deciding game result
    async def game_decide(self):
        # calculating game result
        # Fetch all player's points from Redis
        player_point_keys = redis_client.keys(f"points:{self.room_name}:*")
        #creating a player(username):points dict called player_choices
        player_points = {
            key.split(":")[-1]: redis_client.get(key) for key in player_point_keys
        }
        print(f"player points stored in cache: {player_points}")

        players = list(player_points.keys())
        points = list(player_points.values())


        if len(points) == 0:
            print("no players got points")
            return {"result_status": "draw"}
        elif len(points) == 1:
            # only one player got points
            # thus only a not draw case
            print(f"player: {players[0]} won the game")
            winner = players[0]
        else:
            # both players got points
            # potential draw case
            if points[0] == points[1]:
                # Game draw case
                print("game draw")
                return {"result_status": "draw"}
            elif points[0] > points[1]:
                # player 0 won
                winner = players[0]
                print(f"player: {players[0]} won the game")
            else:
                # player 1 won
                winner = players[1]
                print(f"player: {players[1]} won the game")

        return {"result_status": "not_draw", "winner": winner}

    async def broadcast_round_result_message(self, result):
        # broadcasting game result to whole group(group send)
        content = {
            "type": "round_result",
            "result": result,  # The actual round result
        }

        # incrementing round number
        round_number_key = f"rounds:{self.room_name}:" # Redis key for round number
        current_round = redis_client.get(round_number_key)
        print(f'current round : {current_round}')
        next_round = int(current_round) + 1
        redis_client.set(round_number_key, next_round)

        # Broadcast round result to the group
        await self.channel_layer.group_send(
            self.room_group_name,  # Group name
            {
                "type": "self_send_round_result",  # Custom handler type
                "message": content,         # Message payload
            }
        )

        # Broadcast game result to the group if next_round > 3(all rounds played)
        if next_round > 3:
            await self.broadcast_game_result_message()

    # broadcasts game result to all players in the group
    async def broadcast_game_result_message(self):
        game_result = await self.game_decide()
        print('All rounds played \nsending game result')
        content = {
            "type": "game_result",
            "result": game_result,  # The actual game result
        }

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "self_send_game_result",
                "message": content
            }
        )

        # clearing cache for the players points and round
        await self.clear_cache_game()

    async def self_send_round_result(self, event):
        # sending the message to frontend of current user(self send)
        # Extract the message content from the event
        in_message = event["message"]

        out_message = {
            'type' : 'round_result'
        }
        '''
        structure of in_message
        {
            'type': 'round_result',
            'result': {
                'result_status': 'not_draw' || 'draw',
                'winner': 'John', (may not present in case of draw)
                'choices': {'John': 'paper', 'admin': 'rock'}
            }
        }
        '''

        round_result = in_message.get('result')
        out_message['choices'] = round_result.get('choices')

        result_status = round_result.get('result_status')

        if result_status == 'not_draw':
            
            print("sending win message")
            user = self.scope['user'].username
            if user == round_result['winner']:
                print(f"i {user} won this round")
                out_message['result'] = 'win'
            else:
                print(f"i {user} lost this round")
                out_message['result'] = 'loss'
        else:
            out_message['result'] = 'draw'

        '''
        structure of out_message
        {
            'type': 'round_result',
            'result': 'win' || 'loss' || 'draw',
            'choices': {'John': 'paper', 'admin': 'rock'}
        }
        '''

        # Send the message to the specific WebSocket connection
        await self.send(text_data=json.dumps(out_message))

    async def self_send_game_result(self, event):
        in_message = event["message"]
        print('sending GAME RESULT to frontend')
        out_message = {
            'type' : 'game_result'
        }

        '''
        structure of in_message
        {
            'type': 'game_result',
            'result': {
                'result_status': 'not_draw' || 'draw',
                'winner': {username of winner} (may not present in case of draw)
            }
        }
        '''
        game_result = in_message.get('result')
        result_status = game_result.get('result_status')
        user = self.scope['user']
        username = user.username
        # Fetch GamePlayer object
        try:
            game_player_obj = await sync_to_async(GamePlayer.objects.get)(user=user)
        except GamePlayer.DoesNotExist:
            print(f"Error: GamePlayer object does not exist for user {username}")
            return  # Exit the function if no GamePlayer object exists
        
        # updating gamePlayer fields based on game result and getting out_message ready
        if result_status == 'not_draw':
            if game_result.get('winner') == username:
                out_message['result'] = 'win'
                game_player_obj.wins += 1
                game_player_obj.points += 10
            else:
                out_message['result'] = 'loss'
                game_player_obj.losses += 1
        else:
            out_message['result'] = 'draw'
            game_player_obj.points += 5
        
        game_player_obj.matches_played += 1

        # Save the updated GamePlayer object to database
        await sync_to_async(game_player_obj.save)()
        '''
        structure of out_message
        {
            'type': 'game_result',
            'result': 'win' || 'loss' || 'draw',
        }
        '''
        # sending the message to frontend
        await self.send(text_data=json.dumps(out_message))

    # handle when one player leaves the room
    async def leave(self, content):
        print("inside leave method")
        game_room = await sync_to_async(GameRoom.objects.get)(room_name=self.room_name)
        usernames = await sync_to_async(list)(
            game_room.users.values_list("username", flat=True)
        )
        print(f"usernames: {usernames}")
        if len(usernames) < 2:
            pass
        else:
            if usernames[0] == self.scope['user'].username:
                winner = usernames[1]
            else:
                winner = usernames[0]

            content = {
                "type": "game_result",
                "result": {
                    "result_status": "not_draw",
                    "winner": winner
                }
            }
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "self_send_game_result",
                        "message": content
                    }
                )
            
    # handling play again, when a player wants to play again in same game room
    async def play_again(self, content):
        play_again_key_pattern = f"play_again:{self.room_name}"
        play_again_set = redis_client.get(play_again_key_pattern)
        if play_again_set:
            # deleting previously set play_again 
            redis_client.delete(play_again_key_pattern)
            # need to broadcast a game_start message to frontend
            game_room = await sync_to_async(GameRoom.objects.get)(room_name=self.room_name)
            usernames = await sync_to_async(list)(
                game_room.users.values_list("username", flat=True)
            )
            await self.broadcast_game_start(usernames)
        else:
            redis_client.set(play_again_key_pattern, 1)

    async def clear_cache_round(self):
        # clearing cache after a round
        room_key_pattern = f"game:{self.room_name}:*"  # Pattern for all keys in the room
        room_keys = redis_client.keys(room_key_pattern)
        if room_keys:
            redis_client.delete(*room_keys)  # Delete all keys matching the pattern
            print(f"Cleared cache for room: {self.room_name}")

    async def clear_cache_game(self):
        # clearing cache for points after all rounds played
        player_point_key_pattern = f"points:{self.room_name}:*"  # Pattern for all point keys in the room
        player_point_keys = redis_client.keys(player_point_key_pattern)
        if player_point_keys:
            redis_client.delete(*player_point_keys)  # Delete all keys matching the pattern
            print(f"Cleared cache for player points in the room: {self.room_name}")

        # reset round number cache incase of play again
        round_number_key = f"rounds:{self.room_name}:" # Redis key for round number
        redis_client.set(round_number_key, 1)

        # un-setting the play_again, if set
        play_again_key_pattern = f"play_again:{self.room_name}"
        play_again_set = redis_client.get(play_again_key_pattern)
        if play_again_set:
            redis_client.delete(play_again_key_pattern)


# disconnect part
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print("inside disconnect")
        await self.clear_cache_game()
        await self.remove_user_from_room()
        
    async def remove_user_from_room(self):
        try:
            # Retrieve the game room
            game_room = await sync_to_async(GameRoom.objects.get)(room_name=self.room_name)
            
            if game_room:
                # Decrease user count and remove user from room
                game_room.user_count -= 1
                await sync_to_async(game_room.users.remove)(self.scope["user"])
                
                # Delete the room if it's empty, otherwise save the updated instance
                if game_room.user_count <= 0:
                    await sync_to_async(game_room.delete)()
                else:
                    await sync_to_async(game_room.save)()
                    
                    
        except Exception as e:
            print(f"Error while disconnecting user: {e}")
