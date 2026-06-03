from models.carousel import (
    ArticleMetadata,
    BeforeYouRead,
    BiasOrRhetoricalAnnotation,
    CarouselInput,
    CarouselOutput,
    ClaimOrSourceAnnotation,
    CuiBono,
    EmotionalRegister,
    ExternalSource,
    GoFurtherItem,
    GlobalAnalysis,
    GlobalAnalysisItem,
    Hook,
    LocalAnnotationsSlide,
    PostReadingQuestion,
    QuoteDeepDive,
    Synthesis,
    TermDefinition,
)


def mock_carousel(input: CarouselInput) -> CarouselOutput:
    return CarouselOutput(
        article_metadata=ArticleMetadata(
            url=input.url,
            title=input.title,
            source=input.source,
            published_at=input.published_at,
            article_type="editorial",
        ),
        hook=Hook(
            headline="L'Europe s'indigne — mais seulement pour les siens",
            context_line="Éditorial Le Monde, 22 mai 2026 — après la vidéo de Ben Gvir sur la flottille.",
            why_read="Un éditorial bien écrit qui dénonce une vraie incohérence — et en commet une autre sans le voir.",
            pull_quote="Parce qu'elles ont concerné jusqu'à maintenant des Palestiniens, personne ne s'en est jamais ému.",
        ),
        before_you_read=BeforeYouRead(
            contexts=[
                "La flottille a été interceptée le 20 mai dans des eaux dont le statut international est contesté.",
                "La présence de ressortissants européens parmi les passagers a amplifié la réaction diplomatique.",
            ],
            who_is_speaking=[
                "Signé 'Le Monde' — voix collective de la rédaction, pas un journaliste identifiable.",
                "Un éditorial engage le journal officiellement : c'est une prise de position, pas un reportage.",
                "Le Monde a multiplié les tribunes critiques envers le gouvernement israélien depuis octobre 2023.",
            ],
            important_facts=[
                "La CIJ a ordonné en janvier 2024 à Israël de prendre des mesures pour prévenir les actes génocidaires à Gaza — absent de cet éditorial.",
                "B'Tselem, unique source citée sur les conditions de détention, est régulièrement contestée par les autorités israéliennes.",
            ],
            key_terms=[
                TermDefinition(term="B'Tselem", definition="Organisation israélienne de défense des droits humains qui documente les violations commises dans les territoires occupés."),
                TermDefinition(term="CIJ", definition="Cour internationale de justice — principal organe judiciaire de l'ONU, qui tranche les litiges entre États."),
                TermDefinition(term="Détention administrative", definition="Emprisonnement sans inculpation ni jugement, renouvelable indéfiniment, utilisé par Israël principalement contre des Palestiniens."),
                TermDefinition(term="Flottille", definition="Convoi maritime humanitaire organisé pour tenter de briser le blocus de Gaza et attirer l'attention internationale."),
            ],
            watch_out=[
                "Repérez qui parle dans cet article — et notamment si une des parties directement concernées par les faits est absente.",
                "Notez chaque fois que l'article cite B'Tselem : demandez-vous si d'autres sources sont mobilisées pour les mêmes affirmations.",
                "Observez comment l'article situe la vidéo de Ben Gvir par rapport à des événements similaires passés — ou s'il ne le fait pas.",
            ],
            questions=[
                "Qu'est-ce qui déclenche une réaction diplomatique européenne sur ce conflit — et qu'est-ce qui ne la déclenche pas ?",
                "Quand un média prend position sur un sujet aussi sensible, à qui s'adresse-t-il en priorité ?",
            ],
        ),
        global_analysis=GlobalAnalysis(
            observations=[
                GlobalAnalysisItem(
                    aspect="voix",
                    summary="L'article cite Ben Gvir (par ses actes), Nétanyahou et Saar (pour les condamner), B'Tselem. Aucune voix palestinienne, aucun juriste sur le statut des eaux — pourtant au cœur du contexte.",
                ),
                GlobalAnalysisItem(
                    aspect="angle",
                    summary="L'indignation européenne est prise pour acquise — l'article ne questionne pas pourquoi elle n'a pas existé lors des interceptions précédentes impliquant uniquement des Palestiniens.",
                ),
                GlobalAnalysisItem(
                    aspect="cadre juridique",
                    summary="L'article ne mentionne ni la décision de la CIJ de janvier 2024 ni les négociations en cours — deux éléments qui placeraient les arrestations dans un contexte légal et diplomatique très différent.",
                ),
            ],
            emotional_register=[
                EmotionalRegister(
                    emotion="indignation",
                    how="L'article juxtapose les images de militants humiliés avec le silence passé sur les Palestiniens — le contraste produit un sentiment d'injustice cumulée.",
                    effect="Le lecteur est amené à ressentir que son indignation présente est légitime, mais insuffisante — il aurait dû s'indigner avant.",
                ),
                EmotionalRegister(
                    emotion="honte",
                    how="La France est nommée explicitement parmi les pays qui n'ont pas agi — le lecteur français est directement interpellé.",
                    effect="Le lecteur est invité à associer l'inaction de son gouvernement à une défaillance morale personnelle.",
                ),
            ],
            cui_bono=[
                CuiBono(
                    beneficiary="Les partisans d'une ligne européenne plus ferme envers Israël",
                    explanation="Le cadrage de l'incohérence européenne comme scandaleuse renforce l'argument en faveur de sanctions — sans avoir à les défendre explicitement.",
                ),
                CuiBono(
                    beneficiary="B'Tselem",
                    explanation="Citer B'Tselem comme seule source légitime sur les conditions de détention renforce sa crédibilité institutionnelle sans la soumettre à contradiction.",
                ),
            ],
        ),
        local_annotations=LocalAnnotationsSlide(
            claims_and_sources=[
                ClaimOrSourceAnnotation(
                    quote="les prisons réservées aux Palestiniens sont devenues « des camps de torture »",
                    presentation="attributed_to_source",
                    proves="voix",
                    explanation="Explicitement attribué à B'Tselem avec guillemets et verbe d'attribution — mais aucune voix contradictoire n'est donnée sur ce point précis.",
                    external_sources=[
                        ExternalSource(name="Comité de l'ONU contre la torture (CAT), rapports 2024", supports="validates", evidence_type="testimony", why_read="Corrobore les conditions décrites à partir de témoignages indépendants."),
                        ExternalSource(name="Rapport B'Tselem 'Un véritable enfer' (janvier 2025)", supports="validates", evidence_type="testimony", url=None, reading_time_minutes=20, why_read="Le rapport original — lire directement plutôt qu'à travers la synthèse de l'article."),
                        ExternalSource(name="Service pénitentiaire israélien (IPS)", supports="contradicts", evidence_type="party_statement", why_read="Contestation officielle — sans données indépendantes publiées."),
                    ],
                    confidence=74,
                    confidence_label="likely true",
                ),
                ClaimOrSourceAnnotation(
                    quote="arraisonnée manifestement dans les eaux internationales",
                    presentation="presented_as_established_fact",
                    proves="cadre juridique",
                    explanation='"Manifestement" présente une position juridiquement contestée comme une évidence — aucune attribution, aucun conditionnel.',
                    external_sources=[
                        ExternalSource(name="UNCLOS (Convention des Nations Unies sur le droit de la mer)", supports="neutral", evidence_type="official_data", why_read="Définit le cadre juridique applicable — ne tranche pas le cas spécifique."),
                        ExternalSource(name="Forces de défense israéliennes (IDF)", supports="contradicts", evidence_type="party_statement", why_read="Position officielle israélienne sur la légalité de l'interception."),
                        ExternalSource(name="Freedom Flotilla Coalition", supports="validates", evidence_type="party_statement", why_read="Déclaration des organisateurs sur le lieu d'interception."),
                    ],
                    confidence=68,
                    confidence_label="likely true",
                ),
                ClaimOrSourceAnnotation(
                    quote="une centaine de Palestiniens, selon des décomptes convergents, sont morts en détention en Israël depuis deux ans et demi, contre 230 entre 1967 et 2023",
                    presentation="attributed_to_source",
                    proves="voix",
                    explanation='"Selon des décomptes convergents" attribue sans nommer — B\'Tselem et PHR-IL, deux organisations aux chaînes probatoires distinctes, convergent ; Israël conteste sans publier de décompte alternatif auditable.',
                    external_sources=[
                        ExternalSource(name="Médecins pour les droits de l'homme Israël (PHR-IL)", supports="validates", evidence_type="official_data", why_read="Méthodologie documentée et indépendante de B'Tselem — convergence entre deux chaînes probatoires distinctes."),
                        ExternalSource(name="B'Tselem", supports="validates", evidence_type="testimony", why_read="Source principale du décompte, registres et témoignages croisés."),
                        ExternalSource(name="Administration pénitentiaire israélienne", supports="contradicts", evidence_type="party_statement", why_read="Chiffres officiels inférieurs, sans méthodologie publiée."),
                    ],
                    confidence=70,
                    confidence_label="likely true",
                ),
            ],
            biases_and_rhetoric=[
                BiasOrRhetoricalAnnotation(
                    quote="Représentant d'une extrême droite suprémaciste et raciste décomplexée longtemps rejetée aux marges de la vie politique de l'Etat hébreu",
                    label="étiquetage présenté comme fait",
                    proves="voix",
                    effect="Ben Gvir est décrit, pas cité — remarquez qu'aucune parole directe ne lui est accordée dans tout l'article.",
                ),
                BiasOrRhetoricalAnnotation(
                    quote="seuls trois pays membres de l'Union européenne ont adopté des sanctions à son encontre. La France ne les a pas rejoints à ce jour",
                    label="interpellation directe du lecteur",
                    proves="honte",
                    effect="La France est nommée seule parmi les absents — le lecteur français est mis en face d'une inaction spécifique, pas d'un constat général.",
                ),
                BiasOrRhetoricalAnnotation(
                    quote="Dès août 2024, l'organisation israélienne de défense des droits humains B'Tselem a assuré, à la suite d'une enquête approfondie, que les prisons réservées aux Palestiniens sont devenues « des camps de torture »",
                    label="autorité unique non contrebalancée",
                    proves="B'Tselem",
                    effect="B'Tselem est introduite avec une description valorisante — son statut est établi avant même que ses conclusions ne soient citées.",
                ),
                BiasOrRhetoricalAnnotation(
                    quote="Il fallait en plus les humilier en les montrant, mercredi 20 mai, les mains liées dans le dos, à genoux, le visage contre le sol",
                    label="détail visuel à forte charge émotionnelle",
                    proves="indignation",
                    effect="La description physique précise de l'humiliation produit une image mentale immédiate — remarquez qu'elle précède toute analyse, ce qui ancre émotionnellement le lecteur avant qu'il puisse prendre du recul.",
                ),
            ],
            quote_deep_dive=QuoteDeepDive(
                quote="Parce qu'elles ont concerné jusqu'à maintenant des Palestiniens, personne ne s'en est jamais ému au sein de la coalition au pouvoir, alors qu'elles témoignaient déjà de l'effritement de valeurs qu'Israël a longtemps revendiquées.",
                proves="angle",
                analysis="\"Personne\" est une généralisation — des ONG, des opposants, des juges se sont bien exprimés. Ce que la phrase vise, c'est le silence institutionnel, mais la formule englobe tout. L'indignation est présentée comme conditionnelle à l'identité des victimes — ce qui soulève la question posée avant de lire : qu'est-ce qui déclenche, ou non, une réaction diplomatique ?",
            ),
        ),
        synthesis=Synthesis(
            points=[
                "L'éditorial identifie une vraie asymétrie dans les réactions européennes — et la traite principalement à travers B'Tselem, dont les conclusions sont réelles mais non contrebalancées.",
                "La vidéo de Ben Gvir a provoqué une indignation que des années de rapports sur les Palestiniens n'avaient pas déclenchée — la question de ce qui rend une injustice visible reste entière.",
                "Le cadre juridique de la CIJ, absent de l'article, aurait pu ancrer l'argument dans un droit international contraignant — son absence laisse le raisonnement sur le terrain moral.",
            ]
        ),
        go_further=[
            GoFurtherItem(
                title="Témoignages de détenus palestiniens libérés (dossier 2024–2025)",
                source="Haaretz",
                media_type="article",
                category="question_answer",
                url=None,
                duration_minutes=15,
                why_explore="Témoignages directs de détenus palestiniens libérés — la voix absente de l'éditorial.",
                answers_question="Que disent les organisations palestiniennes elles-mêmes sur les conditions de détention — et pourquoi leur voix est-elle absente de presque tous les médias occidentaux couvrant ce sujet ?",
            ),
            GoFurtherItem(
                title="Occupation of the Palestinian Territories",
                source="Al Jazeera Documentary",
                media_type="documentary",
                category="question_answer",
                url=None,
                duration_minutes=50,
                why_explore="Donne la parole aux Palestiniens directement concernés — perspective quasi absente des médias européens couvrant ce sujet.",
                answers_question="Que disent les organisations palestiniennes elles-mêmes sur les conditions de détention — et pourquoi leur voix est-elle absente de presque tous les médias occidentaux couvrant ce sujet ?",
            ),
            GoFurtherItem(
                title="Gaza flotillas: a history of interceptions since 2010",
                source="The Guardian",
                media_type="article",
                category="deep_dive",
                url=None,
                duration_minutes=10,
                why_explore="Situe cet événement dans une série d'interceptions précédentes — permet de tester si l'indignation décrite est réellement nouvelle.",
                answers_question=None,
            ),
            GoFurtherItem(
                title="Ordonnance de la CIJ sur Gaza : ce qu'elle implique concrètement",
                source="Le Monde Diplomatique",
                media_type="article",
                category="question_answer",
                url=None,
                duration_minutes=12,
                why_explore="Explique la décision de la CIJ de janvier 2024 et ses implications juridiques — le contexte absent de l'éditorial.",
                answers_question="La décision de la CIJ sur Gaza change-t-elle la façon dont vous évaluez l'interception de la flottille ?",
            ),
            GoFurtherItem(
                title="The Hundred Years' War on Palestine",
                source="Rashid Khalidi (livre, 2020)",
                media_type="book",
                category="deep_dive",
                url=None,
                duration_minutes=480,
                why_explore="Donne le contexte historique long que ce type d'éditorial présuppose sans jamais fournir.",
                answers_question=None,
            ),
        ],
        post_reading_questions=[
            PostReadingQuestion(
                question="Pensez-vous que l'identité des victimes influence réellement les réactions diplomatiques — ou que d'autres facteurs expliquent mieux les différences de traitement ?",
                type="topic_substance",
            ),
            PostReadingQuestion(
                question="Les conditions de détention des Palestiniens méritent-elles selon vous la même attention médiatique que celles des ressortissants européens ?",
                type="topic_substance",
            ),
            PostReadingQuestion(
                question="Une ONG qui documente les violations suffit-elle comme source pour qualifier des lieux de détention de 'camps de torture' ?",
                type="article_quality",
            ),
            PostReadingQuestion(
                question="La décision de la CIJ sur Gaza change-t-elle la façon dont vous évaluez l'interception de la flottille ?",
                type="article_quality",
            ),
            PostReadingQuestion(
                question="Auriez-vous lu cet éditorial différemment s'il avait été publié par un média connu pour ses positions pro-israéliennes ?",
                type="reader_bias",
            ),
            PostReadingQuestion(
                question="Appliquez-vous les mêmes exigences de sourçage quand les conclusions d'un article vont dans le sens de vos convictions ?",
                type="reader_bias",
            ),
            PostReadingQuestion(
                question="Que disent les organisations palestiniennes elles-mêmes sur les conditions de détention — et pourquoi leur voix est-elle absente de presque tous les médias occidentaux couvrant ce sujet ?",
                type="blind_spot",
            ),
        ],
    )
