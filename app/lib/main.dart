import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:url_launcher/url_launcher.dart';

void main() {
  runApp(const DiasporaApp());
}

class DiasporaApp extends StatelessWidget {
  const DiasporaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Turkish Diaspora App',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.red,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        fontFamily: 'Roboto',
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;
  
  final List<Widget> _pages = [
    const FeedPage(),
    const NewsPage(),
    const Center(child: Text('Music - Coming Soon')),
    const Center(child: Text('Sports - Coming Soon')),
    const Center(child: Text('Events - Coming Soon')),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Turkish Diaspora App'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              // Trigger refresh
              setState(() {});
            },
          ),
        ],
      ),
      body: _pages[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (int index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home),
            label: 'For You',
          ),
          NavigationDestination(
            icon: Icon(Icons.newspaper),
            label: 'News',
          ),
          NavigationDestination(
            icon: Icon(Icons.music_note),
            label: 'Music',
          ),
          NavigationDestination(
            icon: Icon(Icons.sports_soccer),
            label: 'Sports',
          ),
          NavigationDestination(
            icon: Icon(Icons.event),
            label: 'Events',
          ),
        ],
      ),
    );
  }
}

class FeedPage extends StatefulWidget {
  const FeedPage({super.key});

  @override
  State<FeedPage> createState() => _FeedPageState();
}

class _FeedPageState extends State<FeedPage> {
  List<dynamic> items = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    fetchFeed();
  }

  Future<void> fetchFeed() async {
    try {
      final response = await http.get(
        Uri.parse('http://localhost:8000/v1/feed'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          items = data['items'];
          isLoading = false;
        });
      }
    } catch (e) {
      print('Error fetching feed: $e');
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (items.isEmpty) {
      return const Center(
        child: Text('No news items available'),
      );
    }

    return RefreshIndicator(
      onRefresh: fetchFeed,
      child: ListView.builder(
        padding: const EdgeInsets.all(8),
        itemCount: items.length,
        itemBuilder: (context, index) {
          return NewsCard(item: items[index]);
        },
      ),
    );
  }
}

class NewsPage extends StatefulWidget {
  const NewsPage({super.key});

  @override
  State<NewsPage> createState() => _NewsPageState();
}

class _NewsPageState extends State<NewsPage> {
  List<dynamic> items = [];
  bool isLoading = true;
  String selectedRegion = 'All';
  String selectedLang = 'All';

  @override
  void initState() {
    super.initState();
    fetchNews();
  }

  Future<void> fetchNews() async {
    setState(() {
      isLoading = true;
    });

    try {
      String url = 'http://localhost:8000/v1/news';
      List<String> params = [];
      
      if (selectedRegion != 'All') {
        params.add('region=$selectedRegion');
      }
      if (selectedLang != 'All') {
        params.add('lang=$selectedLang');
      }
      
      if (params.isNotEmpty) {
        url += '?' + params.join('&');
      }

      final response = await http.get(Uri.parse(url));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          items = data['items'];
          isLoading = false;
        });
      }
    } catch (e) {
      print('Error fetching news: $e');
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Filter chips
        Container(
          padding: const EdgeInsets.all(8),
          child: Wrap(
            spacing: 8,
            children: [
              FilterChip(
                label: const Text('All Regions'),
                selected: selectedRegion == 'All',
                onSelected: (bool selected) {
                  setState(() {
                    selectedRegion = 'All';
                  });
                  fetchNews();
                },
              ),
              FilterChip(
                label: const Text('Nederland'),
                selected: selectedRegion == 'Nederland',
                onSelected: (bool selected) {
                  setState(() {
                    selectedRegion = selected ? 'Nederland' : 'All';
                  });
                  fetchNews();
                },
              ),
              FilterChip(
                label: const Text('Türkiye'),
                selected: selectedRegion == 'Türkiye',
                onSelected: (bool selected) {
                  setState(() {
                    selectedRegion = selected ? 'Türkiye' : 'All';
                  });
                  fetchNews();
                },
              ),
            ],
          ),
        ),
        // News list
        Expanded(
          child: isLoading
              ? const Center(child: CircularProgressIndicator())
              : items.isEmpty
                  ? const Center(child: Text('No news items'))
                  : RefreshIndicator(
                      onRefresh: fetchNews,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(8),
                        itemCount: items.length,
                        itemBuilder: (context, index) {
                          return NewsCard(item: items[index]);
                        },
                      ),
                    ),
        ),
      ],
    );
  }
}


// Add this updated NewsCard class to your main.dart (replace the existing NewsCard class)

class NewsCard extends StatefulWidget {
  final Map<String, dynamic> item;

  const NewsCard({super.key, required this.item});

  @override
  State<NewsCard> createState() => _NewsCardState();
}

class _NewsCardState extends State<NewsCard> {
  Map<String, int> reactions = {};
  Set<String> userReactions = {};

  @override
  void initState() {
    super.initState();
    // Initialize reactions from item data
    if (widget.item['reactions'] != null) {
      reactions = Map<String, int>.from(widget.item['reactions']);
    }
  }

  Future<void> toggleReaction(String emoji) async {
    final itemId = widget.item['id'];
    
    try {
      final response = await http.post(
        Uri.parse('http://localhost:8000/v1/reactions'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'item_id': itemId,
          'emoji': emoji,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          reactions = Map<String, int>.from(data['reactions']);
          if (userReactions.contains(emoji)) {
            userReactions.remove(emoji);
          } else {
            userReactions.add(emoji);
          }
        });
      }
    } catch (e) {
      print('Error toggling reaction: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final String title = widget.item['title'] ?? '';
    final String summary = widget.item['summary_nl'] ?? widget.item['summary_tr'] ?? '';
    final List regions = widget.item['regions'] ?? [];
    final List tags = widget.item['tags'] ?? [];
    final String url = widget.item['url'] ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      child: InkWell(
        onTap: () async {
          if (url.isNotEmpty && !url.contains('example.com')) {
            final Uri uri = Uri.parse(url);
            if (await canLaunchUrl(uri)) {
              await launchUrl(uri);
            }
          }
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Title
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              // Summary
              if (summary.isNotEmpty)
                Text(
                  summary,
                  style: Theme.of(context).textTheme.bodyMedium,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              const SizedBox(height: 12),
              // Regions and tags
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  ...regions.map((region) => Chip(
                        label: Text(
                          region,
                          style: const TextStyle(fontSize: 12),
                        ),
                        backgroundColor: Colors.blue.shade100,
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                      )),
                  ...tags.map((tag) => Chip(
                        label: Text(
                          tag,
                          style: const TextStyle(fontSize: 12),
                        ),
                        backgroundColor: Colors.green.shade100,
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                      )),
                ],
              ),
              const SizedBox(height: 12),
              // Emoji reactions
              Row(
                children: [
                  _buildReactionButton('👍', reactions['👍'] ?? 0),
                  _buildReactionButton('❤️', reactions['❤️'] ?? 0),
                  _buildReactionButton('😂', reactions['😂'] ?? 0),
                  _buildReactionButton('🔥', reactions['🔥'] ?? 0),
                  _buildReactionButton('👏', reactions['👏'] ?? 0),
                  const Spacer(),
                  if (!url.contains('example.com'))
                    TextButton.icon(
                      icon: const Icon(Icons.open_in_new, size: 16),
                      label: const Text('Read More'),
                      onPressed: () async {
                        final Uri uri = Uri.parse(url);
                        if (await canLaunchUrl(uri)) {
                          await launchUrl(uri);
                        }
                      },
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildReactionButton(String emoji, int count) {
    final isSelected = userReactions.contains(emoji);
    
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: InkWell(
        onTap: () => toggleReaction(emoji),
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: isSelected ? Colors.blue.shade100 : Colors.grey.shade100,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: isSelected ? Colors.blue.shade300 : Colors.grey.shade300,
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(emoji, style: const TextStyle(fontSize: 16)),
              if (count > 0) ...[
                const SizedBox(width: 4),
                Text(
                  count.toString(),
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected ? Colors.blue.shade700 : Colors.grey.shade700,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}