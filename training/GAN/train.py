import random

from evaluation.seq2seq.evaluate import calculate_loss_on_eval_set
from training.seq2seq.train import save_state
from utils.batching import *
from utils.data_prep import *
from utils.time_utils import *


def train_GAN(config, vocabulary, generator, discriminator, articles, titles, eval_articles, eval_titles, max_length,
              writer):

    n_generator = config['train']['n_generator']
    n_discriminator = config['train']['n_discriminator']  # This is a scaling factor of n_generator
    max_sample_length = config['train']['max_sample_length']
    n_epochs = config['train']['n_epochs']
    batch_size = config['train']['batch_size']
    print_every = config['log']['print_every']
    with_categories = config['train']['with_categories']

    start = time.time()
    print_loss_generator = 0
    print_loss_discriminator = 0
    lowest_loss_generator = 999
    lowest_loss_discriminator = 999

    # TODO: in run experiment -> make sure that: (len(train_articles) / batch_size) % n_normal == 0
    num_batches = int(len(articles) / batch_size)
    n_iters = num_batches * n_epochs

    g_articles = articles
    g_titles = titles
    d_articles = articles * n_discriminator
    d_titles = titles * n_discriminator

    for epoch in n_epochs:
        # shuffle articles and titles (equally)
        c = list(zip(g_articles, g_titles))
        random.shuffle(c)
        g_articles_shuffled, g_titles_shuffled = zip(*c)
        c = list(zip(d_articles, d_titles))
        random.shuffle(c)
        d_articles_shuffled, d_titles_shuffled = zip(*c)

        # split into batches
        g_article_batches = list(chunks(g_articles_shuffled, batch_size))
        g_title_batches = list(chunks(g_titles_shuffled, batch_size))
        d_article_batches = list(chunks(d_articles_shuffled, batch_size))
        d_title_batches = list(chunks(d_titles_shuffled, batch_size))

        count_disc = 0
        batch = 0
        while batch < num_batches:
            # train generator for n_generator batches
            for n in range(n_generator):
                input_variable, input_lengths, target_variable, target_lengths = prepare_batch(batch_size, vocabulary,
                    g_article_batches[batch], g_title_batches[batch], max_length, with_categories)
                loss = generator.train(config, input_variable, input_lengths, target_variable, target_lengths)
                print_loss_generator += loss
                # calculate number of batches processed
                itr_generator = (epoch - 1) * num_batches + batch + 1
                if itr_generator % print_every == 0:
                    print_loss_avg = print_loss_generator / print_every
                    print_loss_generator = 0
                    progress, total_runtime = time_since(start, itr_generator / n_iters, print_loss_generator)
                    start = time.time()
                    print('%s (%d %d%%)' % (progress, itr_generator, itr_generator / n_iters * 100), flush=True)
                    print('Generator loss: %.4f' % print_loss_avg, flush=True)
                    if print_loss_avg < lowest_loss_generator:
                        lowest_loss_generator = print_loss_avg
                        print(" ^ Lowest generator loss so far", flush=True)
                batch += 1
                # train discriminator for n_discriminator batches
                for m in range(n_discriminator):
                    # generate ground truth
                    ground_truth = [1 for _ in batch_size] + [0 for _ in batch_size]
                    ground_truth_batched = Variable(torch.FloatTensor(ground_truth)).unsqueeze(1)
                    # generate fate data
                    real_data_variable, real_data_lengths = prepare_batch(batch_size, vocabulary,
                        d_article_batches[count_disc], d_title_batches[count_disc], max_length, with_categories)
                    fake_data_variable = generator.create_samples(real_data_variable, real_data_lengths,
                                                                  max_sample_length)
                    # concatenate real and fake data
                    d_titles_real_and_fake = torch.cat(real_data_variable, fake_data_variable)  # TODO: verify ok?
                    # train and calculate loss
                    loss = discriminator.train(ground_truth_batched, d_titles_real_and_fake)
                    print_loss_discriminator += loss
                    # calculate number of batches processed
                    itr_discriminator = (epoch - 1) * num_batches + count_disc + 1
                    if itr_discriminator % print_every == 0:
                        print_loss_avg = print_loss_discriminator / print_every
                        print_loss_discriminator = 0
                        print('Discriminator loss: %.4f' % print_loss_avg, flush=True)
                        if print_loss_avg < lowest_loss_discriminator:
                            lowest_loss_discriminator = print_loss_avg
                            print(" ^ Lowest discriminator loss so far", flush=True)
                    count_disc += 1
        # save each epoch
        print("Saving model", flush=True)
        save_state({
            'model_state_encoder': generator.encoder.state_dict(),
            'model_state_decoder': generator.decoder.state_dict(),
        }, config['experiment_path'] + "/" + config['save']['save_file_generator'])
        save_state({
            'model': discriminator.model.state_dict()
        }, config['experiment_path'] + "/" + config['save']['save_file_discriminator'])

        generator.encoder.eval()
        generator.decoder.eval()
        calculate_loss_on_eval_set(config, vocabulary, generator.encoder, generator.decoder, generator.mle_criterion,
                                   writer, epoch, max_length, eval_articles, eval_titles)
        generator.encoder.train()
        generator.decoder.train()