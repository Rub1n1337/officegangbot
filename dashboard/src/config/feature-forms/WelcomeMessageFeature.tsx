import { Divider, Flex, SimpleGrid } from '@chakra-ui/react';
import { TextAreaForm } from '@/components/forms/TextAreaForm';
import { UseFormRender, WelcomeMessageFeature } from '@/config/types';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useRouter } from 'next/router';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { WelcomePreview } from '@/components/feature/WelcomePreview';
import { useGuildPreview } from '@/api/hooks';

const schema = z.object({
  message: z.string().min(1),
  channel: z.string().optional(),
});

type Input = z.infer<typeof schema>;

export const useWelcomeMessageFeature: UseFormRender<WelcomeMessageFeature> = (data, onSubmit) => {
  const { register, reset, handleSubmit, formState, control, watch } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      channel: data.channel ?? undefined,
      message: data.message ?? '',
    },
  });

  const guildId = useRouter().query.guild as string;
  const { guild } = useGuildPreview(guildId);
  const message = watch('message');

  return {
    component: (
      <Flex direction="column" gap={3}>
        <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
          <ChannelSelectForm
            control={{
              label: 'Channel',
              description: 'Where to send the welcome message',
            }}
            controller={{ control, name: 'channel' }}
          />
          <TextAreaForm
            control={{
              label: 'Message',
              description: 'The welcome message. Use {user.mention} to mention the new member and {server.name} for the server name.',
              error: formState.errors.message?.message,
            }}
            placeholder="Welcome {user.mention} to {server.name}! We're glad to have you."
            {...register('message')}
          />
        </SimpleGrid>
        <Divider my={1} />
        <WelcomePreview message={message ?? ''} serverName={guild?.name ?? 'your server'} />
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const data = await onSubmit(
        JSON.stringify({
          message: e.message,
          channel: e.channel,
        })
      );

      reset({
        ...data,
        channel: data.channel ?? undefined,
      });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
