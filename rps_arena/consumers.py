import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import GameRoom, GamePlayer

class GameConsumer(AsyncWebsocketConsumer):
# Connect part
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"game_{self.room_name}"
        self.game_state = {}

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
        await self.send_player_joined_message(usernames)

# Receive part
    async def receive(self, text_data):
        content = json.loads(text_data)
        message_type = content.get("type")
        print(f"recieved message: {content}")

        message_handlers = {
            "player_joined": self.send_player_joined_message,
            "my_choice": self.my_choice,
            "opponent_choice": self.opponent_choice,
            "game_result": self.game_result_message,
        }

        handler = message_handlers.get(message_type)

        if handler:
            await handler(content)
        else:
            print(f"Unhandled message type: {message_type}")

    # player joined handling
    async def send_player_joined_message(self, message):
        # sending message to whole group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "player_joined_message",
                "message": message
            }
        )
    # sending message to frontend
    async def player_joined_message(self, event):
        await self.send(text_data = json.dumps({
            "type": "player_joined",
            "message": event["message"]
        }))

    #handling my_choice
    async def my_choice(self, content):
        content = content.get('content')
        player_choice = content.get('choice')
        player = self.scope['user'].username
        print(f"In my_choice: {content}")
        #storing player's choices
        if self.room_name not in self.game_state:
            self.game_state[self.room_name] = {}
            self.game_state[self.room_name][player] = player_choice
        # storing only if player choice not in game_state
        elif not self.game_state[self.room_name].get(player):
            self.game_state[self.room_name][player] = player_choice
            content = {
                'player': player,
                'choice': player_choice,
                'sender_id': self.scope['user'].id
            }
            # broadcasting my_choice as opponent choice
            await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "broadcast_choice",
                "message": content
            }
        )

        #calculating result if both players made the choice
        print(f"In my_choice: {self.game_state[self.room_name]}")
        if len(self.game_state[self.room_name]) == 2:
            result = await self.game_decide()
            await self.game_result_message(result)

    async def broadcast_choice(self, event):
        await self.send(text_data = json.dumps({
            "type": "opponent_choice",
            "message": event["message"]
        }))

    #handling opponent_choice
    async def opponent_choice(self, content):
        content = content.get('content')
        print(f"In opponent_choice: {content}")
        # only process message when sender is not this user
        if content.get('sender_id') != self.scope['user'].id:
            player_choice = content.get('choice')
            player = content.get('player')

            #storing player's choices
            if self.room_name not in self.game_state:
                self.game_state[self.room_name] = {}
                self.game_state[self.room_name][player] = player_choice
            # storing only if player choice not in game_state
            elif not self.game_state[self.room_name].get(player):
                self.game_state[self.room_name][player] = player_choice
                content = {
                    'player': player,
                    'choice': player_choice,
                }
                # sending opponent's choice to frontend
                await self.send(text_data = json.dumps({
                    "type": "opponent_choice",
                    "message": content,
                }))

            #calculating result if both players made the choice
            print(f"In opponent_choice: {self.game_state[self.room_name]}")
            if len(self.game_state[self.room_name]) == 2:
                result = await self.game_decide()
                #sending game result to frontend
                await self.game_result_message(result)

    async def send_player_choice_game(self, content):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "player_choice_message",
                "result": content.get("choice")
            }
        )

    async def game_result_message(self, result):
        await self.send(text_data = json.dumps({
            "type": "game_result",
            "result": result
        }))
        # clearing state after result
        self.game_state[self.room_name] = {}

    async def game_decide(self):
        player1, player2 = self.game_state[self.room_name].keys()
        choice1, choice2 = self.game_state[self.room_name].values()

        if choice1 == choice2:
            print("It's a draw")
            return {
                "draw": "draw",
                player1: choice1,
                player2: choice2,
            }
        
        elif (choice1 == 'rock' and choice2 == 'scissors') or \
             (choice1 == 'scissors' and choice2 == 'paper') or \
             (choice1 == 'paper' and choice2 == 'rock'):
            print(f'User {player1} won with {choice1} against {choice2}!')
            return {
                "winner": player1,
                "looser": player2,
                player1: choice1,
                player2: choice2,
            }
        
        else:
            print(f'User {player2} won with {choice2} against {choice1}!')
            return {
                "winner": player2,
                "looser": player1,
                player1: choice1,
                player2: choice2,
            }
# disconnect part
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.remove_user_from_room()
        
    
    @sync_to_async(thread_sensitive=False)
    def remove_user_from_room(self):
        try:
            # Retrieve the game room
            game_room = GameRoom.objects.filter(room_name=self.room_name).first()
            
            if game_room:
                # Decrease user count and remove user from room
                game_room.user_count -= 1
                game_room.users.remove(self.scope["user"])
                
                # Delete the room if it's empty, otherwise save the updated instance
                if game_room.user_count <= 0:
                    game_room.delete()
                else:
                    game_room.save()
                    
        except Exception as e:
            print(f"Error while disconnecting user: {e}")
