import json
import redis.asyncio as redis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"game_{self.room_name}"

        # Initialize Redis connection
        self.redis = await redis.from_url("redis://127.0.0.1:6379")

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"User connected: {self.scope['user'].id} in room: {self.room_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        # Close Redis connection
        await self.redis.close()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        choice = text_data_json['message']
        user_id = self.scope['user'].id


        # Store the user's choice in Redis
        await self.redis.hset(f"choices_{self.room_group_name}", user_id, choice)
        
        # Retrieve choices for the game state check
        choices = await self.get_choices_from_redis()
        print(f"current choices: {choices}")
        if len(choices) == 2:
            message = self.game_decide(choices)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_message',
                    'message': message
                }
            )

            # Clear choices after the game round
            await self.redis.delete(f"choices_{self.room_group_name}")

    async def game_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({'message': message}))

    def game_decide(self, choices):
        user_ids = list(choices.keys())
        choice1 = choices[user_ids[0]]
        choice2 = choices[user_ids[1]]

        if choice1 == choice2:
            return "It's a draw!"
        elif (choice1 == 'rock' and choice2 == 'scissors') or \
             (choice1 == 'scissors' and choice2 == 'paper') or \
             (choice1 == 'paper' and choice2 == 'rock'):
            return f'User {user_ids[0]} won with {choice1} against {choice2}!'
        else:
            return f'User {user_ids[1]} won with {choice2} against {choice1}!'

    async def get_choices_from_redis(self):
        """Helper method to retrieve choices from Redis."""
        choices = await self.redis.hgetall(f"choices_{self.room_group_name}")
        # Convert binary data to strings
        return {int(user_id.decode('utf-8')): choice.decode('utf-8') for user_id, choice in choices.items()}
